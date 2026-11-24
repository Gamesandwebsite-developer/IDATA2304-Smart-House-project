import asyncio

from .SimulationBuilder import create_nodes
from .server import IntermediateServer


# Run the application process
async def run(host: str = "127.0.0.1", port: int = 8081) -> None:
    server = IntermediateServer(host, port)
    # Run the operation and handle possible errors
    try:
        for node in create_nodes().values():
            await server.add_simulated_node(node)

        await server.start()
    finally:
        await server.stop()


# Start the application
def main() -> None:
    # Run the operation and handle possible errors
    try:
        asyncio.run(run())
    except OSError as error:
        raise SystemExit(f"Could not start Smart House server: {error}") from error
    except KeyboardInterrupt:
        print("\nServer shut down.")


if __name__ == "__main__":
    main()
