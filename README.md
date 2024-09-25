# NWC Proxy

This project is a Lightning Network Wallet Connect (NWC) proxy that consists of two main services: an LNURL server and an NWC node. It facilitates Lightning Network transactions and provides an API for interacting with a Lightning Network wallet.

## Project Structure

The project is composed of two main services:

1. **LNURL Server**: A Python-based server that handles LNURL-related functionality.
2. **NWC Node**: A Node.js-based server that uses Nostr wallet connect (NWC).

## Prerequisites

- Docker
- Docker Compose

## Configuration

Before running the project, you need to set up the following environment variables:

- `NWC_CONNECTION_STRING`: The connection string for the Lightning Network wallet.
- `NODE_BASE_URL`: The base URL for the NWC node (default: http://nwc_node:3000).
- `LN_ADDRESS_DOMAIN`: The domain for Lightning addresses (default: localhost:8000).
- `LN_USERNAME`: The username for Lightning addresses (default: nwc).

You can set these variables in your environment or create a `.env` file in the project root directory.

## Running the Project

To run the project using the `docker-compose.local.yml` file, follow these steps:

1. Make sure you have Docker and Docker Compose installed on your system.

2. Clone the repository and navigate to the project directory.

3. Set up the required environment variables as mentioned in the Configuration section.

4. Run the following command to start the services:

   ```
   docker-compose -f docker-compose.local.yml up --build
   ```

   This command will build the Docker images for both services and start the containers.

5. Once the services are up and running, you can access them at:
   - LNURL Server: http://localhost:8000
   - NWC Node: http://localhost:3000

## API Endpoints

### LNURL Server

- `GET /`: Welcome message
- `GET /health`: Health check endpoint
- `GET /lnurlp/{username}`: LNURL Pay endpoint
- `GET /lnurlp/{username}/callback`: Generate invoice endpoint
- `GET /.well-known/lnurlp/{username}`: LNURL Pay endpoint (alternative)

### NWC Node

- `GET /`: Hello message
- `GET /api/hello`: API hello message
- `POST /api/run-command`: Execute Lightning Network wallet commands

## Development

The project uses Docker for containerization, making it easy to develop and deploy. The `docker-compose.local.yml` file defines the services and their configurations for local development.

To make changes to the project:

1. Modify the source code in the `lnurl_server` or `nwc_node` directories.
2. Rebuild and restart the containers using the `docker-compose -f docker-compose.local.yml up --build` command.

## Notes

- Make sure to keep your `NWC_CONNECTION_STRING` and other sensitive information secure and not commit them to version control.
- The `startup.sh` script contains example environment variable values. In a production environment, you should set these variables securely and not rely on this script.

For more detailed information about each service, refer to the source code in the respective directories.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file in the project root for the full license text.

The MIT License is a permissive open-source license that allows you to use, modify, and distribute this software for both private and commercial purposes. It comes with no warranties and requires that you include the original copyright notice and license terms in any copy or substantial portion of the software.