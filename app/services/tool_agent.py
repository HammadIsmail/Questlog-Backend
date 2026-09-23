"""
OpenAI SDK-powered Tool Calling Agent for Questlog.
Handles CRUD database operations and user dialogue via native OpenAI function/tool calling.
"""
import json
import logging
import uuid
from typing import List, Dict, Any, Optional

import httpx
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.models.goal import Goal, GoalStatus
from app.schemas.goal import GoalOut
from app.services.scoring_service import award_goal_completion

logger = logging.getLogger(__name__)

# ── Tool Definitions for OpenAI Function Calling ──
QUEST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_quest",
            "description": "Create and add a new quest/task to the user's questlog. Call this when the user specifies a task along with priority and/or deadline/duration, or when answering a previous priority/deadline clarification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Concise quest or task title"},
                    "priority": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                        "description": "Task priority level. Defaults to 'medium' if not explicitly stated."
                    },
                    "estimated_minutes": {
                        "type": "integer",
                        "description": "Estimated duration in minutes (e.g., 30, 60, 120)."
                    },
                    "category": {
                        "type": "string",
                        "description": "Category e.g. Coding, Work, Study, Quest"
                    }
                },
                "required": ["title", "priority", "estimated_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "Call this function when the user wants to add a task, but has NOT specified priority (High, Medium, Low) or deadline/duration. This prompts the user for the missing priority and deadline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_title": {"type": "string", "description": "The title of the task mentioned"},
                    "clarification_question": {
                        "type": "string",
                        "description": "Question to ask the user, e.g., 'What priority (High, Medium, or Low) and deadline should I set for [task]?'"
                    }
                },
                "required": ["task_title", "clarification_question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_all_quests",
            "description": "Delete ALL quests from the user's questlog. Call this whenever the user asks to clear all, delete all, or remove all tasks/quests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirm": {"type": "boolean", "description": "Always true"}
                },
                "required": ["confirm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_quest",
            "description": "Delete a specific quest from the user's questlog by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quest_id": {"type": "string", "description": "The UUID of the quest to delete"},
                    "quest_title": {"type": "string", "description": "The title of the quest"}
                },
                "required": ["quest_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_quest",
            "description": "Update an existing quest in the questlog (change priority, estimated duration/deadline, or title).",
            "parameters": {
                "type": "object",
                "properties": {
                    "quest_id": {"type": "string", "description": "The UUID of the matching quest to update"},
                    "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"], "description": "New priority level"},
                    "estimated_minutes": {"type": "integer", "description": "New estimated duration in minutes"},
                    "new_title": {"type": "string", "description": "New title if user requested a rename"}
                },
                "required": ["quest_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_quest",
            "description": "Mark a quest as completed and award user experience points.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quest_id": {"type": "string", "description": "The UUID of the quest to complete"},
                    "quest_title": {"type": "string", "description": "The title of the quest"}
                },
                "required": ["quest_id"]
            }
        }
    }
]


def get_openai_client() -> Optional[AsyncOpenAI]:
    """Initialize AsyncOpenAI client targeting Groq or OpenAI."""
    custom_http = httpx.AsyncClient(timeout=25.0)
    if settings.groq_api_key:
        return AsyncOpenAI(
            api_key=settings.groq_api_key.strip(),
            base_url="https://api.groq.com/openai/v1",
            http_client=custom_http,
        )
    elif settings.openai_api_key:
        return AsyncOpenAI(
            api_key=settings.openai_api_key.strip(),
            http_client=custom_http,
        )
    return None


async def run_tool_agent(
    user_input: str,
    conversation_history: List[Dict[str, str]],
    current_user: User,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Execute tool-calling workflow with the OpenAI SDK.
    Interacts with the database based on function calls invoked by the model.
    """
    # ── Fast Deterministic Delete-All Shortcut ──
    lower_input = user_input.lower().strip()
    delete_all_triggers = [
        "delete all", "remove all", "clear all", "delete my all", "delete all my",
        "remove all my", "clear all my", "delete every task", "delete everything"
    ]
    if any(t in lower_input for t in delete_all_triggers):
        all_goals_res = await db.execute(select(Goal).where(Goal.user_id == current_user.id))
        all_goals = all_goals_res.scalars().all()
        del_ids = [g.id for g in all_goals]
        for g in all_goals:
            await db.delete(g)
        await db.commit()
        return {
            "created_goals": [],
            "updated_goals": [],
            "deleted_goal_ids": del_ids,
            "assistant_reply": "All your quests have been cleared from your quest log.",
            "action": "delete_all",
        }

    client = get_openai_client()
    if not client:
        return {
            "created_goals": [],
            "updated_goals": [],
            "deleted_goal_ids": [],
            "assistant_reply": "AI service is currently unavailable. Ensure GROQ_API_KEY or OPENAI_API_KEY is configured.",
            "action": "chat",
        }

    # Fetch active user goals for context
    active_goals_res = await db.execute(
        select(Goal).where(Goal.user_id == current_user.id).order_by(Goal.created_at.desc()).limit(50)
    )
    existing_goals = active_goals_res.scalars().all()
    goals_context = [
        {
            "id": str(g.id),
            "title": g.title,
            "priority": g.priority,
            "estimated_minutes": (g.target_duration_seconds or 0) // 60,
            "status": g.status.value if hasattr(g.status, "value") else str(g.status),
        }
        for g in existing_goals
    ]

    system_prompt = f"""You are the Quest Master AI companion in Questlog.
You have direct access to database tools for managing quests:
- `create_quest`: Add a quest (only when priority or deadline is known or answered).
- `ask_clarification`: When a user specifies a task WITHOUT priority or deadline.
- `update_quest`: Update an existing quest's priority or duration.
- `delete_quest`: Delete a specific quest.
- `delete_all_quests`: Delete all quests.
- `complete_quest`: Mark a quest done.

CURRENT USER QUESTS IN DATABASE:
{json.dumps(goals_context)}

INSTRUCTIONS:
1. Always call the appropriate tool when managing quests.
2. If the user asks a question about their day, productivity, or tips, answer warmly and conversationally without calling tools.
3. If user says 'delete all' or 'clear all', call `delete_all_quests`.
4. If user specifies a task without priority or deadline, call `ask_clarification`.
"""

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    # Append recent history (last 6 turns)
    for turn in conversation_history[-6:]:
        messages.append({
            "role": turn.get("role", "user"),
            "content": turn.get("text", "")
        })

    # Append latest user input
    messages.append({"role": "user", "content": user_input})

    model_name = settings.groq_model if settings.groq_api_key else "gpt-4o-mini"

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=QUEST_TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )
    except Exception as e:
        logger.error("OpenAI SDK tool calling failed: %s", e)
        return {
            "created_goals": [],
            "updated_goals": [],
            "deleted_goal_ids": [],
            "assistant_reply": f"Encountered an issue communicating with the AI service: {e}",
            "action": "chat",
        }

    choice = response.choices[0]
    message = choice.message

    created_records: List[GoalOut] = []
    updated_records: List[GoalOut] = []
    deleted_ids: List[uuid.UUID] = []
    assistant_reply = message.content or ""
    action = "chat"

    # ── Execute Tool Calls Against Database ──
    if message.tool_calls:
        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments or "{}")
            except Exception:
                fn_args = {}

            logger.info("Executing tool call: %s with args %s", fn_name, fn_args)

            # 1. Delete All Quests
            if fn_name == "delete_all_quests":
                all_goals_res = await db.execute(select(Goal).where(Goal.user_id == current_user.id))
                all_goals = all_goals_res.scalars().all()
                for g in all_goals:
                    deleted_ids.append(g.id)
                    await db.delete(g)
                await db.commit()
                action = "delete_all"
                assistant_reply = "All your quests have been cleared from your quest log."

            # 2. Delete Single Quest
            elif fn_name == "delete_quest":
                raw_id = fn_args.get("quest_id")
                if raw_id:
                    try:
                        gid = uuid.UUID(str(raw_id))
                        target = next((g for g in existing_goals if g.id == gid), None)
                        if target:
                            await db.delete(target)
                            await db.commit()
                            deleted_ids.append(gid)
                            action = "delete"
                            assistant_reply = f"Removed '{target.title}' from your active quests."
                    except Exception as ex:
                        logger.error("Error deleting quest: %s", ex)

            # 3. Create Quest
            elif fn_name == "create_quest":
                title = fn_args.get("title", "").strip()
                prio = fn_args.get("priority", "medium").lower()
                mins = int(fn_args.get("estimated_minutes", 30))
                cat = fn_args.get("category", "Quest")

                if title:
                    new_g = Goal(
                        user_id=current_user.id,
                        title=title,
                        category=cat,
                        priority=prio if prio in ["critical", "high", "medium", "low"] else "medium",
                        target_duration_seconds=mins * 60,
                        status="pending",
                    )
                    db.add(new_g)
                    await db.flush()
                    await db.commit()
                    created_records.append(GoalOut.model_validate(new_g))
                    action = "create"
                    assistant_reply = f"Added '{title}' with {prio.capitalize()} priority ({mins}m) to your questlog!"

            # 4. Ask Clarification
            elif fn_name == "ask_clarification":
                q = fn_args.get("clarification_question")
                task_t = fn_args.get("task_title", "this quest")
                action = "ask_clarification"
                assistant_reply = q or f"What should be the priority (High, Medium, or Low) and deadline for '{task_t}'?"

            # 5. Update Quest
            elif fn_name == "update_quest":
                raw_id = fn_args.get("quest_id")
                if raw_id:
                    try:
                        gid = uuid.UUID(str(raw_id))
                        target = next((g for g in existing_goals if g.id == gid), None)
                        if target:
                            if fn_args.get("priority"):
                                target.priority = fn_args["priority"].lower()
                            if fn_args.get("estimated_minutes"):
                                target.target_duration_seconds = int(fn_args["estimated_minutes"]) * 60
                            if fn_args.get("new_title"):
                                target.title = fn_args["new_title"].strip()
                            await db.flush()
                            await db.commit()
                            updated_records.append(GoalOut.model_validate(target))
                            action = "update"
                            assistant_reply = f"Updated '{target.title}' to {target.priority} priority."
                    except Exception as ex:
                        logger.error("Error updating quest: %s", ex)

            # 6. Complete Quest
            elif fn_name == "complete_quest":
                raw_id = fn_args.get("quest_id")
                if raw_id:
                    try:
                        gid = uuid.UUID(str(raw_id))
                        target = next((g for g in existing_goals if g.id == gid), None)
                        if target:
                            target.status = GoalStatus.completed
                            await db.flush()
                            await award_goal_completion(db, current_user.id, target)
                            await db.commit()
                            updated_records.append(GoalOut.model_validate(target))
                            action = "complete"
                            assistant_reply = f"Great work! Completed '{target.title}' and awarded points!"
                    except Exception as ex:
                        logger.error("Error completing quest: %s", ex)

    if not assistant_reply:
        assistant_reply = "Ready for your next quest!"

    return {
        "created_goals": created_records,
        "updated_goals": updated_records,
        "deleted_goal_ids": deleted_ids,
        "assistant_reply": assistant_reply,
        "action": action,
    }
