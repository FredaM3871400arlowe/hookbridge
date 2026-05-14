# hookbridge

A lightweight webhook relay server with filtering rules and payload transformation support.

## Installation

```bash
pip install hookbridge
```

## Usage

Start the relay server and define your routing rules in a simple YAML config:

```yaml
# hookbridge.yml
routes:
  - name: github-to-slack
    source: /incoming/github
    destination: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
    filter:
      field: action
      equals: opened
    transform:
      template: '{"text": "New PR: {{ payload.pull_request.title }}"}'
```

Then run the server:

```bash
hookbridge start --config hookbridge.yml
```

Send a webhook to `http://localhost:8080/incoming/github` and hookbridge will filter, transform, and forward it to your destination.

### Programmatic Usage

```python
from hookbridge import RelayServer, Route

server = RelayServer(port=8080)
server.add_route(Route(
    source="/incoming/github",
    destination="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
))
server.start()
```

## Features

- **Filtering** – Drop or allow events based on payload field values
- **Transformation** – Reshape payloads using Jinja2 templates
- **Multi-destination** – Fan out a single webhook to multiple endpoints
- **Logging** – Built-in request logging and replay support

## License

MIT © hookbridge contributors