import pytest

from tg_search.api.auth_store import AuthStore

pytestmark = [pytest.mark.unit]


class TestAuthStoreTokenPersistence:
    @pytest.mark.asyncio
    async def test_issue_token_persist_and_reload(self, tmp_path):
        token_store_file = tmp_path / "auth_tokens.json"
        store = AuthStore(token_store_file=str(token_store_file))

        token_obj = await store.issue_token(
            user_id=12345,
            phone_number="+8613800138000",
            username="persist_user",
        )
        assert token_store_file.exists()

        reloaded_store = AuthStore(token_store_file=str(token_store_file))
        loaded = await reloaded_store.validate_token(token_obj.token)

        assert loaded is not None
        assert loaded.user_id == 12345
        assert loaded.username == "persist_user"

    @pytest.mark.asyncio
    async def test_revoke_token_updates_persistent_file(self, tmp_path):
        token_store_file = tmp_path / "auth_tokens.json"
        store = AuthStore(token_store_file=str(token_store_file))

        token_obj = await store.issue_token(
            user_id=20001,
            phone_number="+10000000000",
        )
        revoked = await store.revoke_token(token_obj.token)
        assert revoked is True

        reloaded_store = AuthStore(token_store_file=str(token_store_file))
        loaded = await reloaded_store.validate_token(token_obj.token)

        assert loaded is None

    @pytest.mark.asyncio
    async def test_expired_tokens_are_dropped_on_reload(self, tmp_path):
        token_store_file = tmp_path / "auth_tokens.json"
        expired_store = AuthStore(token_store_file=str(token_store_file), token_ttl=-1)
        expired_token = await expired_store.issue_token(
            user_id=999,
            phone_number="+10000000001",
        )

        reloaded_store = AuthStore(token_store_file=str(token_store_file))
        loaded = await reloaded_store.validate_token(expired_token.token)

        assert loaded is None
