# Protocol description

_For each of the design choices provide a short justification: why did you choose to design it the way you did?_

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

_A short introduction: "This document describes \_ \_"_

## 2. Terminology

_Terminology: a list of special terms you use_

## 3. Transport protocol

_The underlying transport protocol you use (TCP or UDP or both)_

## 4. Port number

_The used port number_

## 5. Architecture

_The overall architecture:_

- _Who are the actors (nodes) in your solution?_
- _Who are the clients, who is/are the server(s)?_

## 6. Information flow

_The flow of information: when and how the messages are sent?_

## 7. Protocol type

_The type of your protocol:_

- _Is your protocol connection-oriented or connection-less?_
- _Is the protocol state-full or state-less?_

## 8. Constants

_The different types and special values (constants) used_

## 9. Message format

_The message format:_

- _The allowed message types (sensor messages, command messages)_
- _The type of marshalling used (fixed size, separators, TLV?)_
- _Which messages are sent by which node? For example, are some messages only sent by the control-panel node?_

## 10. Error handling

_The different errors that can occur and how each node should react on the errors. For example, what if a message in an unexpected format is received? Is it ignored, or does the recipient send a reply with an error code?_

## 11. Realistic scenario

_Describe a realistic scenario: what would happen from user perspective and what messages would be sent over the network?_

## 12. Reliability mechanisms

_The reliability mechanisms in your protocol (handling of network errors), if you have any_

## 13. Security mechanisms

_The security mechanisms in your protocol, if you have any_

## 14. Assumptions

_Assumptions if you made any_
