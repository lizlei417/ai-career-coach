"""UI adapters: request observation and language metadata, without changing AI behavior."""
import hashlib
from coach.errors import CoachError


class ObservedClient:
    def __init__(self, client, state):
        self.client, self.state = client, state

    def generate(self, schema, system, payload):
        try:
            result = self.client.generate(schema, system, payload)
        except CoachError:
            self.state['connection_status'] = 'failed'
            raise
        self.state['connection_status'] = 'verified'
        return result


def connection_state(state, config):
    signature = hashlib.sha256((config.api_key + '\0' + config.model).encode()).hexdigest()
    if state.get('connection_signature') != signature:
        state['connection_signature'] = signature
        state['connection_status'] = 'unverified' if config.api_key else 'offline'
    if not config.api_key:
        return 'offline'
    return state.get('connection_status', 'unverified')
