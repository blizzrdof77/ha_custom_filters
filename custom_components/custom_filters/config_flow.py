"""Config flow."""
from homeassistant import config_entries

from .const import DOMAIN, COMPONENT_TITLE


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        return self.async_create_entry(title=COMPONENT_TITLE, data={})
