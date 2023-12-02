# 🍌 Banana Phone API 🍌

Banana Phone API 📞 is a relay API that acts as a bridge between clients and larger language models like LM Studio Server or similar platforms. It features a suite of functionalities including API key-based access control, automatic message formatting (autostyle), and real-time streaming responses from language models.

## 🎉 Features

- **🔑 API Key Verification**: Secure the API by granting access only to requests with valid API keys.
- **💅 Automatic Message Styling (Autostyle)**: Customizes model interactions with message prefixes, suffixes, and stop sequences.
- **🔁 Response Streaming**: Supports streaming language model responses for interactive sessions.
- **🔧 Model Configuration Flexibility**: Easily add and manage language model configurations via the `models.json` file.

## 🚀 Getting Started

To get Banana Phone API up and ringing, follow the steps below.

### Prerequisites

- Python 3.x
- pip for installing Python packages

### Installation

1. Clone the repository and step into the new directory:

```sh
git clone https://github.com/your-username/banana-phone.git
cd banana-phone
```

2. Use the `ring.sh` script to prepare the environment and kick off the API server:

```sh
bash ring.sh --port 3456
```

### Configuration

Adjust the API settings by tweaking the `.env` file variables:

- `LOCAL_PORT`: The port Banana Phone API will listen on.
- `DESTINATION_API`: The destination API URL, like the LM Studio Server.
- `ENDPOINT_COMPLETIONS`: Endpoint for getting completions.
- `ENDPOINT_MODELS`: Endpoint for retrieving available models.
- `API_KEYS`: List of API keys, comma-separated, authorizing access to Banana Phone API.
- `WAN_ENABLED`: Toggle (`false` or `true`) to control remote host access.
- `AUTOSTYLE`: Enable (`true`) or disable (`false`) autostyle for formatting messages.
- `SYSTEM_MSG`: Default message used when a query lacks a system message.
- `SYSTEM_OVERRIDE`: Set (`true`) to replace existing system messages with `SYSTEM_MSG`.

Command-line arguments for `ring.sh` to override config settings:

- `--port <port_number>`: Define the port number.
- `--api-url <url>`: Update the destination API URL.
- `--sys <system_message>`: Set the system message.
- `--forcesys`: Ensure system message is applied.
- `--tmux`: Utilize `tmux` for session control.
- `--wan`: Enable access from anywhere, not just localhost.
- `--nostyle`: Turn off message autostyling.
- `--reload`: Auto-reload the server upon file changes.

### 📝 Adding Models to `models.json`

To integrate additional language models:

- Define the stop tokens, message prefixes, and suffixes in `models.json`.
- Add a model configuration object matching the format of existing entries.

Example:

```json
{
  "NewModelConfig": {
    "stops": ["<end>"],
    "sysPrefix": "System says: ",
    "sysSuffix": "\n---\n",
    "prefix": "User asks: ",
    "suffix": "\nReply: ",
    "models": ["shiney-new-model"]
  }
}
```

Ensure the model IDs in the `models` array match those returned by the API's model endpoint.

### ⚠️ Disclaimer

Enabling `--wan` poses security risks, especially if:

- No API key is set (i.e., `API_KEYS` is empty).
- Your network's firewall leaves the specified port open.

For safer remote access, consider establishing a Cloudflare Tunnel or setting up a reverse proxy rather than using the WAN option directly.

## 🎶 This README was composed with the help of ChatGPT 🎶
