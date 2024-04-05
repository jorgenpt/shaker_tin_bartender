import asyncio
import discord
from google.oauth2 import service_account
from google.cloud import firestore
from google.api_core.datetime_helpers import DatetimeWithNanoseconds
from google.cloud.firestore_v1.watch import DocumentChange, ChangeType
from google.cloud.firestore_v1.base_document import DocumentSnapshot
import os
from typing import Callable


if 'FIRESTORE_EMULATOR_HOST' in os.environ:
    print(f"Using emulator {os.environ['FIRESTORE_EMULATOR_HOST']}")
    # credentials = service_account.Credentials.from_service_account_file('mockServiceAccountKey.json')
else:
    print(f"Using live environment")
    credentials = service_account.Credentials.from_service_account_file('serviceAccountKey.json')


class Bartender(discord.Client):
    notification_channels: list[discord.TextChannel] = []

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
    
    async def on_guild_available(self, guild: discord.Guild):
        print(f'Guild available {guild}')
        for channel in guild.channels:
            if channel.name == 'shaker-tin':
                print(f"Found channel: {channel}")
                self.notification_channels.append(channel)

    async def notify(self, changes: list[DocumentChange]):
        await asyncio.sleep(4)
        for change in changes:
            if change.type != ChangeType.ADDED:
                continue
            doc = change.document.to_dict()
            message = None
            if doc['audit_event'] == 'add':
                if doc['audit_type'] == 'LiquorType':
                    message = f":new: **Product** *{doc["after"]["name"]}*"
                elif doc['audit_type'] == 'Bottle':
                    message = f":new: **Bar code** `{doc["after"]["barcode"]}`"
            elif doc['audit_event'] == 'update' and doc['audit_type'] == 'LiquorType' and 'name' in doc['after']:
                message = f":pencil: **Product** *{doc['before']['name']}* :arrow_right: *{doc['after']['name']}*"
                # TODO: Tag and category updates

            if message:
                async with asyncio.TaskGroup() as tg:
                    for channel in self.notification_channels:
                        tg.create_task(channel.send(content=message))


class ShakerTinWatcher:
    def __init__(self, firestore_client: firestore.Client, notification_fn: Callable[[list[DocumentChange]], None]):
        collection_ref = firestore_client.collection('audit').order_by("audit_time", direction=firestore.Query.ASCENDING).start_after({'audit_time': '2024-04-03T20:28:24.391624'})
        # TODO: Do we need to watch a query with a limit instead? This'll get a huge `doc_snapshot` eventually.
        self._collection_watch = collection_ref.on_snapshot(self.on_snapshot)
        self._notification = notification_fn

    def unsubscribe(self):
        self._collection_watch.unsubscribe()

    def on_snapshot(self, _doc_snapshot: list[DocumentSnapshot], changes: list[DocumentChange], read_time: DatetimeWithNanoseconds):
        print(repr(changes))
        print(repr(read_time))
        self._notification(changes)


async def main():
    running_loop = asyncio.get_running_loop()
    firestore_client = firestore.Client(credentials=credentials)
    intents = discord.Intents.default()
    bartender_client = Bartender(intents=intents)

    def notify(changes: list[DocumentChange]):
        asyncio.run_coroutine_threadsafe(bartender_client.notify(changes), running_loop).result()

    shaker_tin_watcher = ShakerTinWatcher(firestore_client, notify)
    await bartender_client.start(open('bot_secret.txt', 'r').read().strip())
    shaker_tin_watcher.unsubscribe()


if __name__ == '__main__':
    asyncio.run(main())