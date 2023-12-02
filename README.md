# 🍌 Banana Phone API 🍌

Banana Phone API 📞 is a relay API that acts as a bridge between clients and larger language model inferencing servers. It is specifically designed to compliment LM Studio Server, but should be compatible with any, OpenAI-compatible endpoints. It features a suite of functionalities including API key-based access control, automatic message formatting to match the active model (some setup required), and real-time streaming responses from language models. It is lightweight and kind-hearted.

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

2. Rename .env.example to .env and configure it (see [[Configuration]]):

```sh
cp .env.example .env
nano .env   # or use any other text editor
```

3. Launch `ring.sh` to build the virtual environment, install necessary dependencies within that environment, and kick off the API server:

```sh
chmod +X ring.sh # only required the first time you run it
./ring.sh --port 3456
```


### Configuration

Adjust the API settings by tweaking the `.env` file variables:

- `LOCAL_PORT`: The port Banana Phone API will listen on.
- `DESTINATION_API`: The destination API URL, like the LM Studio Server.
- `ENDPOINT_COMPLETIONS`: The endpoint on the estination API for getting completions.
- `ENDPOINT_MODELS`: The endpoint on the destination API for retrieving available models.
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

#### Tips:
- When you specify API keys in the .env file, make sur eyou separate them by commas without spaces: just,like,so.
- Specifying any API keys bars queries that don't include them in their header. Set API_KEYS to "" for effective glasnost.
- Use the same format for API keys as OpenAI uses when querying, i.e., `Authorization: Bearer {{key}}`.

### 📝 Adding Models to `models.json` for automatic prompt formatting:

`models.json` includes premade configurations for Alpaca, ChatML, Llama2, Mistral, Orca, Phind, Vicuna, and Zephyr prompt formats, and has populated these configurations with a handful of currently popular models for automatic matching. To add more models under an existing configuation, simply take the model name or a sufficiently unique portion of a model name, taking care to match the case, and add it to the models array within the larger configuration dictionary. For example, if you wanted to add Mistral 7b, you would add it like so:

``` models.json
{
  ... other configurations ...
  "Mistral": {
    "models": [
      "mistral instruct",
      "mistral 7b" # <--- simply add it here!
    ],
    "prefix": "\n[INST] ",
    "stops": [
      "[/INST]",
      "[INST]",
      "</s>"
    ],
    "suffix": "[/INST]\n",
    "sysPrefix": "",
    "sysSuffix": "\n<s>"
  },
  ... other configurations ...
}
```

Similarly, you can add entirely new configurations by replicating the structure of existing ones and filling the relevant information prefixes, suffixes, and stops, which are all readily found on `HuggingFace`.

#### Tips:
- Ensure the model IDs in the `models` array match those returned by the API's model endpoint, or at least a sufficiently unique portion of them.
- You may encounter unexpected behavior if you use overly broad model shortnames such that the model in use matches more than one configuration.
- JSON formatting is notoriously persnickity. A missing comma, curly bracket, or even inadvertently using curly instead of straight quotation marks will likely break the whole script.
- Consider a tool like `OK JSON` if you find yourself editing this or other JSONs frequently.

### ⚠️ Disclaimer

Enabling `--wan` poses security risks, especially if:

- No API key is set (i.e., `API_KEYS` is empty).
- Your network's firewall leaves the specified port open.

For safer remote access, consider establishing a Cloudflare Tunnel or setting up a reverse proxy rather than using the WAN option directly.

## 🎶 This README was composed with the help of ChatGPT 🎶
