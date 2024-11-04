import asyncio
from app.engine import Engine


def run():
    try:
        loop = asyncio.get_event_loop()
        engine = Engine()
        loop.create_task(engine.start_app())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(engine.stop_app())


if __name__ == '__main__':
    run()
