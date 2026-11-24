# Protocol description

## Contents

- [Introduction](#1-introduction)
- [Terminology](#2-terminology)
- [Transport protocol](#3-transport-protocol)
- [Port number](#4-port-number)
- [Architecture](#5-architecture)
- [Information flow](#6-information-flow)
- [Protocol type](#7-protocol-type)
- [Constants](#8-constants)
- [Message format](#9-message-format)
- [Error handling](#10-error-handling)
- [Realistic scenario](#11-realistic-scenario)
- [Reliability mechanisms](#12-reliability-mechanisms)
- [Security mechanisms](#13-security-mechanisms)
- [Assumptions](#14-assumptions)

## 1. Introduction

This document describes the communication protocol implemented by our Smart House project. A user at a control panel client can list the nodes in a house, read sensors and actuators, change an actuator, and update a simulated sensor reading. The client sends JSON requests over TCP to a central server, which validates each request, routes it to the right node, and sends back a JSON response.

## 2. Terminology

| Term                   | Meaning                                                                                                                                                                                         |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Access level           | A string in the request payload, describing the user's role: `admin`, `owner`, `technician`, or `guest`                                                                                         |
| Command                | The kind of request: `READ`, `WRITE`, `LIST_NODES`, `UPDATE_SENSOR`, `REGISTER_NODE`                                                                                                                                              |
| Address                | An optional hierarchical component address in the style `level/room/node/component`, where the first three parts are the node ID, and the last part is the component name                       |
| Central server         | The TCP server that decodes requests, checks permissions, dispatches commands, and returns responses                                                                                            |
| Control panel / client | The program that builds requests and communicates with the server. The interactive menu is implemented in `cli.py`                                                                         |
| Frame                  | One packet carried over TCP with a length prefix of 4 bytes. The length prefix identifies how many bytes of JSON follow, letting the receiver split the TCP byte stream into individual packets |
| Node                   | A registered `SensorActuatorNode`, acting as a simulated device in the house with sensors and/or actuators. It stores its sensor readings and actuator states in memory                         |
| Packet                 | A JSON object consisting of the sender's device ID and type, a timestamp, and a command payload                                                                                                 |
| Payload                | The part of the packet with the actual request or answer                                                                                                                                        |
| Resource / component   | A named sensor or actuator on a node, e.g. `temperature` or `door_lock`                                                                                                                         |

## 3. Transport protocol

The control panel, central server, and sensor-actuator nodes use TCP. The implementation uses Python's asynchronous stream APIs (`asyncio`), which provide a reliable, ordered byte stream while the connection remains open.

TCP does not preserve message boundaries, so the application adds a length prefix to every packet. A four-byte unsigned integer in network byte order (`!I`) gives the number of bytes in the packet body. The packet body follows immediately.

The length does not include the four-byte prefix. The body is the UTF-8 encoding of a JSON packet, with a newline appended by `Packet.encode()`. The receiver uses the length prefix, not the newline, to read the complete body.

Both requests and responses use the same framing. A client may send multiple request/response exchanges over one connection; the interactive client performs them sequentially.

## 4. Port number

The server defaults to `127.0.0.1:8081` (IPv4 loopback, TCP). The default server startup registers its nodes and listens at this address. The `IntermediateServer` constructor accepts a different host and port, so these defaults can be changed by the program using it.

The default loopback binding makes the server reachable only from the same host. The default simulated nodes listen on separate, OS-assigned loopback ports.

## 5. Architecture

```
[Control panel] <--TCP request/response--> [Central server] <--TCP request/response--> [Node]
```

- **Control panel** = client. Creates `Packet` objects and sends their encoded bytes. The interactive client offers options to list nodes, read sensors and actuator states, control an actuator, update a simulated reading, and quit. Several can connect at the same time.
- **Central server** discovers nodes with `LIST_NODES` and forwards component commands to the correct node. Its TCP connection handler reads framed packets and passes each body to `RequestHandler`.
- **Nodes** = simulated devices that listen for server commands. They generate sensor readings and store their own actuator states.

**Why:** one central server means the control panels only need to know one address.

## 6. Information flow

For each operation:

1. The client creates a packet with a command payload and encodes it as JSON.
2. The client sends the four-byte body length followed by the body.
3. The server reads exactly four bytes, checks the declared length, then reads exactly that many body bytes.
4. `RequestHandler` decodes the JSON, checks required fields and access, and resolves the node/component. The server forwards component commands over TCP, answers `LIST_NODES` from its registry, and starts a new node listener for `REGISTER_NODE`.
5. The server sends one framed response packet.
6. The client reads the response length and body, decodes the packet, and uses the response payload.

The supported commands are:

- **`LIST_NODES`:** Returns the IDs of all registered nodes, their device types, and the names of their sensors and actuators. No target node is needed.
- **`READ`:** Returns the current value of a named sensor or actuator on a target node.
- **`WRITE`:** Attempts to set a named actuator to a supplied state. The value must match that actuator's configured type and allowed values/range.
- **`UPDATE_SENSOR`:** Updates a named simulated sensor on a target node. The manual reading stays in place until the node restarts. Control panels pull readings as needed to keep the exchange request/response.

- **`REGISTER_NODE`:** Registers a simulated node with the supplied components. Admin and Owner can use this command. The new node runs until the server stops.

For `READ`, `WRITE`, and `UPDATE_SENSOR`, a request can identify the component directly with `target_node_id` and a command-specific field (`resource`, `actuator`, or `sensor`). It can instead provide `address`; the handler derives the node ID and component from that address. The control panel has helpers for addressed `READ` and `WRITE` requests.

## 7. Protocol type

The protocol is connection-oriented because it uses TCP. The client establishes a connection to the server and can exchange multiple request-and-response messages over that connection before closing it.

At the application level, the system is stateful. The server keeps its node registry in memory. Each node keeps its current sensor readings and actuator states in memory. This is to ensure that every control panel client reads the same value from a specific sensor, if requested a read.

## 8. Constants

### Transport and timing

| Constant             |                                 Value | Meaning                                                                                 |
| -------------------- | ------------------------------------: | --------------------------------------------------------------------------------------- |
| Default host         |                           `127.0.0.1` | Server bind address and client target                                                   |
| Default port         |                                `8081` | TCP port                                                                                |
| Maximum message body |             `1,048,576` bytes (1 MiB) | Client checks outgoing requests and incoming responses; listeners check incoming requests and outgoing responses |
| Client timeout       |                          `10` seconds | Applied to connection setup, send drain, and response reads                             |
| Length prefix        | 4 bytes, unsigned, network byte order | Body length; prefix is not included in the length                                       |

### Command names

The command strings are `LIST_NODES`, `READ`, `WRITE`, `UPDATE_SENSOR`, and `REGISTER_NODE`.

### Access-level names and permissions

Role matching is case-insensitive because the access-control code lowercases the supplied string.

| Role         | Implemented permissions                                                  |
| ------------ | ------------------------------------------------------------------------ |
| `admin`      | All recognized commands, including writing `door_lock`                   |
| `owner`      | All recognized commands, including writing `door_lock`                   |
| `technician` | `READ`, `LIST_NODES`, and `UPDATE_SENSOR`; `WRITE` except to door-lock actuators |
| `guest`      | `READ` and `LIST_NODES`; `WRITE` except to door-lock actuators |

The control panel starts as `guest` and can switch roles from the menu. These roles simulate permissions and require no login.

### Device types and value rules

The packet's `device_type` field is sent as a number and decoded as the corresponding enum. Sensor IDs start with `0x0`, actuator IDs with `0x1`, and system-node IDs with `0x2`.

| Device type            | Numeric ID | Configured value rule                   |
| ---------------------- | ---------: | --------------------------------------- |
| `TEMPERATURE_SENSOR`   |    `0x001` | Finite number from `-100` through `150` |
| `LIGHT_SENSOR`         |    `0x002` | Finite number from `0` through `100000` |
| `HUMIDITY_SENSOR`      |    `0x003` | Finite number from `0` through `100`    |
| `MOTION_SENSOR`        |    `0x004` | Finite number from `0` through `1`      |
| `SMOKE_FLAME_DETECTOR` |    `0x005` | Finite number from `0` through `1`      |
| `UNKNOWN_ACTUATOR`     |    `0x100` | String `ON` or `OFF`                    |
| `IRRIGATOR`            |    `0x101` | String `ON` or `OFF`                    |
| `FAN`                  |    `0x102` | String `ON` or `OFF`                    |
| `HEATER`               |    `0x103` | String `ON` or `OFF`                    |
| `DOOR_LOCK`            |    `0x104` | String `LOCKED` or `UNLOCKED`           |
| `THERMOSTAT_ACTUATOR`  |    `0x105` | Finite number from `-100` through `150` |
| `CONTROL_PANEL`        |    `0x200` | No sensor/actuator value                |
| `PHONE`                |    `0x201` | No sensor/actuator value                |
| `SERVER`               |    `0x202` | No sensor/actuator value                |
| `SIMULATED_NODE`       |    `0x203` | No sensor/actuator value                |

Boolean values are not accepted as numbers. The value rules come from `device_types.json` and are applied when adding or updating a node component or writing an actuator; they are not a general validation of every packet field.

The numeric ranges make categories clear and leave room for additional types. Add a type to `device_types.json` with a unique ID, then restart the server and clients. For example, a `PRESSURE_SENSOR` can use `{"id": 6, "supported_commands": ["READ"], "value_type": "float", "value_range": [950, 1050]}`. A `WINDOW_OPENER` can use `{"id": 262, "supported_commands": ["READ", "WRITE"], "value_type": "string", "allowed_values": ["OPEN", "CLOSED"]}`. Sensors use IDs from `0x000` through `0x0FF` and actuators use `0x100` through `0x1FF`. An unrecognized number cannot be decoded as a `DeviceType`.

## 9. Message format

### Packet encoding

The packet body is a UTF-8 JSON object with these fields:

| Field         | Type              | Meaning                                                                        |
| ------------- | ----------------- | ------------------------------------------------------------------------------ |
| `device_id`   | string            | Sender ID in a request. The server sets this to `server` in a response         |
| `device_type` | integer           | Device type enum value                                                         |
| `timestamp`   | integer or `null` | Unix time in seconds. Generated from the current time when a packet is created |
| `payload`     | object or `null`  | Command fields in a request, or result/error fields in a response              |

Example request body:

```json
{
  "device_id": "admin_user",
  "device_type": 512,
  "timestamp": 1763895600,
  "payload": {
    "command": "READ",
    "target_node_id": "temp_node_1",
    "resource": "temperature",
    "access_level": "admin"
  }
}
```

The example timestamp is just illustrative. The program generates the timestamp when it constructs a packet.

### Request payload fields

All commands include `command`. The control-panel helpers also include `access_level`. The handler defaults a missing `access_level` to `guest`.

| Command         | Required/used payload fields                                        | Effect                                                                    |
| --------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `LIST_NODES`    | `command`                                                           | Lists registered nodes.                                                   |
| `READ`          | `target_node_id` and `resource`, or `address`                       | Reads a sensor or actuator. The response includes `resource` and `value`. |
| `WRITE`         | `target_node_id`, `actuator`, and `state`, or `address` and `state` | Changes an actuator if the actuator exists and `state` is valid.          |
| `UPDATE_SENSOR` | `target_node_id`, `sensor`, and `value`, or `address` and `value`   | Updates an existing simulated sensor if `value` is valid.                 |

`REGISTER_NODE` takes a `node_id` and a non-empty `components` list. Each component has a unique `name`, a device `type` name, and an initial `value`. The success response includes `node_id`.

The optional `address` format is exactly four non-empty slash-separated parts: `level/room/node/component`. Parts cannot be `.` or `..`, and cannot have leading or trailing whitespace. The first three parts are joined with `/` and looked up as the node ID; the last part is used as the component. An address is accepted only for `READ`, `WRITE`, and `UPDATE_SENSOR`.

Example addressed request:

```json
{
  "device_id": "admin_user",
  "device_type": 512,
  "timestamp": 1763895600,
  "payload": {
    "command": "READ",
    "address": "house/ground/temperature_node/temperature",
    "access_level": "admin"
  }
}
```

For this request, the registered node ID must be `house/ground/temperature_node`.

### Responses

The server returns a packet whose `device_id` is `server`. Successful payloads include `"status": "success"`. Error payloads include `"status": "error"` and a human-readable `"message"`.

Examples of successful payloads:

```json
{
  "status": "success",
  "nodes": {
    "temp_node_1": {
      "device_type": "TEMPERATURE_SENSOR",
      "sensors": ["temperature", "humidity"],
      "actuators": ["fan", "thermostat"],
      "sensor_types": {"temperature": "TEMPERATURE_SENSOR", "humidity": "HUMIDITY_SENSOR"},
      "actuator_types": {"fan": "FAN", "thermostat": "THERMOSTAT_ACTUATOR"}
    }
  }
}
```

```json
{ "status": "success", "resource": "temperature", "value": 20.0 }
```

```json
{ "status": "success", "actuator": "door_lock", "new_state": "UNLOCKED" }
```

`LIST_NODES`, `UPDATE_SENSOR`, and `REGISTER_NODE` responses use `DeviceType.SERVER`. `READ` and `WRITE` success responses use the target node's device type. Error responses use `DeviceType.SERVER`. The server does not assign numeric error codes.

### Which parts send which messages

- The control-panel client sends command requests.
- The server sends one result or error response for each complete, length-valid request that it processes.
- The server sends discovery and component commands to each node. Nodes answer over TCP. Discovery includes component type maps so the panel can interpret readings and actuator input.

## 10. Error handling

The protocol reports most request errors as a framed JSON packet with `"status": "error"` and a descriptive `"message"`. Examples include:

- Invalid JSON/packet structure, missing or invalid payload, or missing/invalid command.
- Invalid access level, denied command, unsupported use of `address`, or malformed address.
- Missing/invalid target node ID, unknown node, unknown resource, invalid actuator/sensor name, or invalid value.
- Unknown command.

The request handler returns these error packets and the server's connection loop can continue to process later frames on that connection.

The TCP layer also handles framing and connection errors:

- A zero-length or greater-than-1-MiB body length causes the server to send an `Invalid message size` error response and close the connection.
- If a peer disconnects before a complete header or body arrives, the server logs the disconnect and closes the connection; it cannot process an incomplete request.
- Connection reset, broken pipe, and operating-system connection errors are logged by the server and terminate that connection.
- The client rejects request bodies outside the permitted size before sending them. It rejects invalid response sizes and raises `ConnectionError` for connect/read/write timeouts or unexpected server disconnects.
- Packet decoding errors in the client or server are not converted into numeric protocol error codes. The client-side helper can raise a `ValueError` if a response packet is invalid.

The client timeout is 10 seconds for connection setup, draining outgoing data, and reading the response header/body. Listeners also limit frame-body reads and send drain to 10 seconds. The server allows up to 8 seconds for a forwarded command so it can report an unavailable node to the panel.

## 11. Realistic scenario

Suppose the server is running with its default nodes and an admin uses the control panel to read the temperature:

1. The client connects to `127.0.0.1:8081`.
2. It creates a `READ` packet with `device_id` `admin_user`, device type `512` (`CONTROL_PANEL`), and a payload naming node `temp_node_1`, resource `temperature`, and access level `admin`.
3. The client sends a four-byte body length followed by the JSON packet bytes.
4. The server reads the complete frame. The request handler decodes it, checks the role, and forwards the request to `temp_node_1`, which returns its `temperature` value (e.g. `20.0`).
5. The server returns a framed packet with `device_id` `server`, device type `1` (`TEMPERATURE_SENSOR`), and payload similar to:

   ```json
   { "status": "success", "resource": "temperature", "value": 20.0 }
   ```

6. The client reads and decodes the response and displays the value.

If the user instead tries to change `door_lock` to `UNLOCKED` as a guest, the handler denies the request and responds with an error packet. With `admin` selected, the write succeeds and the in-memory actuator state changes. The implementation does not contact a physical lock.

## 12. Reliability mechanisms

TCP provides ordered, reliable delivery of bytes while a connection is active. Since TCP does not preserve message boundaries, each packet body is preceded by a four-byte length, and the client and server use `readexactly` to receive complete frames. The client limits outgoing requests and incoming responses to 1 MiB, and the listeners apply the same limit to requests and responses.

The client uses a 10-second timeout for connection setup, sending, and receiving responses. If a connection closes before a complete frame arrives, the exact read detects the incomplete message and the connection is closed.

## 13. Security mechanisms

The server applies the permissions in section 8 using the simulated role sent by the control panel. The node listeners run on loopback and accept commands containing an internal token generated automatically at startup.

## 14. Assumptions

The client and server are assumed to use the same packet format, command names, device-type IDs, and value rules. A target node must be registered with the server before a request can access it. Nodes generate readings every three seconds and hold readings and actuator states in memory. `UPDATE_SENSOR` overrides a reading for the current node session.

Each request contains one command and receives one response. The protocol does not define server-pushed notifications or subscriptions, and responses have no correlation ID. The four-byte frame length counts the encoded JSON body, including its trailing newline but excluding the length prefix. The client must connect to the host and port where the server is listening, and the configured defaults are `127.0.0.1:8081`.
