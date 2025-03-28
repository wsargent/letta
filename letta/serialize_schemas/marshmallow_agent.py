from typing import Dict

from marshmallow import fields, post_dump, pre_load

import letta
from letta.orm import Agent
from letta.schemas.agent import AgentState as PydanticAgentState
from letta.schemas.user import User
from letta.serialize_schemas.marshmallow_agent_environment_variable import SerializedAgentEnvironmentVariableSchema
from letta.serialize_schemas.marshmallow_base import BaseSchema
from letta.serialize_schemas.marshmallow_block import SerializedBlockSchema
from letta.serialize_schemas.marshmallow_custom_fields import EmbeddingConfigField, LLMConfigField, ToolRulesField
from letta.serialize_schemas.marshmallow_message import SerializedMessageSchema
from letta.serialize_schemas.marshmallow_tag import SerializedAgentTagSchema
from letta.serialize_schemas.marshmallow_tool import SerializedToolSchema
from letta.server.db import SessionLocal


class MarshmallowAgentSchema(BaseSchema):
    """
    Marshmallow schema for serializing/deserializing Agent objects.
    Excludes relational fields.
    """

    __pydantic_model__ = PydanticAgentState

    FIELD_VERSION = "version"
    FIELD_MESSAGES = "messages"
    FIELD_MESSAGE_IDS = "message_ids"
    FIELD_IN_CONTEXT_INDICES = "in_context_message_indices"
    FIELD_ID = "id"

    llm_config = LLMConfigField()
    embedding_config = EmbeddingConfigField()

    tool_rules = ToolRulesField()

    messages = fields.List(fields.Nested(SerializedMessageSchema))
    core_memory = fields.List(fields.Nested(SerializedBlockSchema))
    tools = fields.List(fields.Nested(SerializedToolSchema))
    tool_exec_environment_variables = fields.List(fields.Nested(SerializedAgentEnvironmentVariableSchema))
    tags = fields.List(fields.Nested(SerializedAgentTagSchema))

    def __init__(self, *args, session: SessionLocal, actor: User, **kwargs):
        super().__init__(*args, actor=actor, **kwargs)
        self.session = session

        # Propagate session and actor to nested schemas automatically
        for field in self.fields.values():
            if isinstance(field, fields.List) and isinstance(field.inner, fields.Nested):
                field.inner.schema.session = session
                field.inner.schema.actor = actor
            elif isinstance(field, fields.Nested):
                field.schema.session = session
                field.schema.actor = actor

    @post_dump
    def sanitize_ids(self, data: Dict, **kwargs):
        """
        - Removes `message_ids`
        - Adds versioning
        - Marks messages as in-context
        - Removes individual message `id` fields
        """
        data = super().sanitize_ids(data, **kwargs)
        data[self.FIELD_VERSION] = letta.__version__

        message_ids = list(data.pop(self.FIELD_MESSAGE_IDS, []))

        # NOTE: currently we don't support out-of-context messages since it has a bunch of system message spams
        # TODO: support out-of-context messages
        messages = []

        # loop through message in the *same* order is the in-context message IDs
        data[self.FIELD_IN_CONTEXT_INDICES] = []
        for i, message in enumerate(data.get(self.FIELD_MESSAGES, [])):
            # if id matches in-context message ID, add to `messages`
            if message[self.FIELD_ID] in message_ids:
                data[self.FIELD_IN_CONTEXT_INDICES].append(i)
            messages.append(message)

        # remove ids
        for message in messages:
            message.pop(self.FIELD_ID, None)  # Remove the id field
        data[self.FIELD_MESSAGES] = messages

        return data

    @post_dump
    def hide_tool_exec_environment_variables(self, data: Dict, **kwargs):
        """Hide the value of tool_exec_environment_variables"""

        for env_var in data.get("tool_exec_environment_variables", []):
            # need to be re-set at load time
            env_var["value"] = ""
        return data

    @pre_load
    def check_version(self, data, **kwargs):
        """Check version and remove it from the schema"""
        version = data[self.FIELD_VERSION]
        if version != letta.__version__:
            print(f"Version mismatch: expected {letta.__version__}, got {version}")
        del data[self.FIELD_VERSION]
        return data

    @pre_load
    def remap_in_context_messages(self, data, **kwargs):
        """
        Restores `message_ids` by collecting message IDs where `in_context` is True,
        generates new IDs for all messages, and removes `in_context` from all messages.
        """
        messages = data.get(self.FIELD_MESSAGES, [])
        for msg in messages:
            msg[self.FIELD_ID] = SerializedMessageSchema.generate_id()  # Generate new ID

        message_ids = []
        in_context_message_indices = data.pop(self.FIELD_IN_CONTEXT_INDICES)
        for idx in in_context_message_indices:
            message_ids.append(messages[idx][self.FIELD_ID])

        data[self.FIELD_MESSAGE_IDS] = message_ids

        return data

    class Meta(BaseSchema.Meta):
        model = Agent
        exclude = BaseSchema.Meta.exclude + (
            "project_id",
            "template_id",
            "base_template_id",
            "sources",
            "source_passages",
            "agent_passages",
            "identities",
            "is_deleted",
            "groups",
        )
