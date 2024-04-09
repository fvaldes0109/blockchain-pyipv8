import os
from asyncio import run
import random

from ipv8.community import Community, CommunitySettings
from ipv8.configuration import ConfigBuilder, Strategy, WalkerDefinition, default_bootstrap_defs
from ipv8.lazy_community import lazy_wrapper
from ipv8.messaging.payload_dataclass import dataclass
from ipv8.types import Peer
from ipv8.util import run_forever
from ipv8_service import IPv8


@dataclass(msg_id=1)  # The value 1 identifies this message and must be unique per community
class MyMessage:
    amount: int  # We add an integer (technically a "long long") field "clock" to this message


class MyCommunity(Community):
    community_id = os.urandom(20)

    def __init__(self, settings: CommunitySettings) -> None:
        super().__init__(settings)
        # Register the message handler for messages (with the identifier "1").
        self.add_message_handler(MyMessage, self.on_message)
        # The Lamport clock this peer maintains.
        # This is for the example of global clock synchronization.
        self.balance = 100

    def started(self) -> None:
        async def start_communication() -> None:
            # If we have not started counting, try boostrapping
            # communication with our other known peers.
            for p in self.get_peers():
                to_send = random.randint(0, self.balance)
                self.balance -= to_send
                self.ez_send(p, MyMessage(to_send))

        # We register an asyncio task with this overlay.
        # This makes sure that the task ends when this overlay is unloaded.
        # We call the 'start_communication' function every 5.0 seconds, starting now.
        self.register_task("start_communication", start_communication, interval=5.0, delay=0)

    @lazy_wrapper(MyMessage)
    def on_message(self, peer: Peer, payload: MyMessage) -> None:
        # Update our Lamport clock.
        self.balance += payload.amount
        print(self.my_peer, "sent", payload.amount, "to", peer, " - Current balance:", self.balance)


async def start_communities() -> None:
    for i in [1, 2, 3]:
        builder = ConfigBuilder().clear_keys().clear_overlays()
        builder.add_key("my peer", "medium", f"ec{i}.pem")
        builder.add_overlay("MyCommunity", "my peer",
                            [WalkerDefinition(Strategy.RandomWalk,
                                              10, {'timeout': 3.0})],
                            default_bootstrap_defs, {}, [('started',)])
        await IPv8(builder.finalize(),
                   extra_communities={'MyCommunity': MyCommunity}).start()
    await run_forever()


run(start_communities())
