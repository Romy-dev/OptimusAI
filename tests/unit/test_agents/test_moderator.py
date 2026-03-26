"""Tests for the moderator agent."""

import pytest

from app.agents.moderator import ModeratorAgent


@pytest.fixture
def agent():
    return ModeratorAgent()


@pytest.fixture
def brand():
    return {
        "brand_name": "Test Brand",
        "banned_words": ["concurrent", "arnaque"],
        "banned_topics": ["politique"],
        "sensitive_topics": ["remboursement"],
    }


class TestModeratorAgent:
    @pytest.mark.asyncio
    async def test_approves_clean_content(self, agent, brand):
        result = await agent.execute({
            "content": "Découvrez nos nouveaux tissus wax colorés !",
            "content_type": "post",
            "brand_context": brand,
        })
        assert result.success
        assert result.output["approved"] is True
        assert result.output["action"] == "approved"

    @pytest.mark.asyncio
    async def test_blocks_toxic_content(self, agent, brand):
        result = await agent.execute({
            "content": "Va te faire foutre connard",
            "content_type": "post",
            "brand_context": brand,
        })
        assert result.success
        assert result.output["approved"] is False
        assert "toxicity" in result.output["flags"]

    @pytest.mark.asyncio
    async def test_flags_banned_words(self, agent, brand):
        result = await agent.execute({
            "content": "Notre concurrent fait du mauvais travail",
            "content_type": "post",
            "brand_context": brand,
        })
        assert result.success
        assert any("banned_word" in f for f in result.output["flags"])

    @pytest.mark.asyncio
    async def test_flags_banned_topics(self, agent, brand):
        result = await agent.execute({
            "content": "En cette période de politique électorale, votez pour le bon candidat",
            "content_type": "post",
            "brand_context": brand,
        })
        assert result.success
        assert any("banned_topic" in f for f in result.output["flags"])

    @pytest.mark.asyncio
    async def test_flags_sensitive_topics(self, agent, brand):
        result = await agent.execute({
            "content": "Pour votre remboursement, contactez-nous",
            "content_type": "post",
            "brand_context": brand,
        })
        assert result.success
        assert any("sensitive_topic" in f for f in result.output["flags"])

    @pytest.mark.asyncio
    async def test_detects_phone_numbers(self, agent, brand):
        result = await agent.execute({
            "content": "Appelez-nous au 22670123456 pour commander",
            "content_type": "post",
            "brand_context": brand,
        })
        assert "possible_phone_number" in result.output["flags"]
