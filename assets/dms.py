from assets.aicommunication import get_response


async def handle_dm(message):
    response = get_response(message.content)

    await message.channel.send(response)