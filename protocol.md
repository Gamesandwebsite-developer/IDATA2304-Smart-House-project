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
*A short introduction: "This document describes _ _"*  
  

## 2. Terminology
*Terminology: a list of special terms you use*  


## 3. Transport protocol
*The underlying transport protocol you use (TCP or UDP or both)*


## 4. Port number
*The used port number*


## 5. Architecture
*The overall architecture:*
- *Who are the actors (nodes) in your solution?*
- *Who are the clients, who is/are the server(s)?*

## 6. Information flow
*The flow of information: when and how the messages are sent?*


## 7. Protocol type
*The type of your protocol:*
- *Is your protocol connection-oriented or connection-less?*
- *Is the protocol state-full or state-less?*


## 8. Constants
*The different types and special values (constants) used*


## 9. Message format
*The message format:*
- *The allowed message types (sensor messages, command messages)*
- *The type of marshalling used (fixed size, separators, TLV?)*
- *Which messages are sent by which node? For example, are some messages only sent by the control-panel node?*


## 10. Error handling
*The different errors that can occur and how each node should react on the errors. For example, what if a message in an unexpected format is received? Is it ignored, or does the recipient send a reply with an error code?*


## 11. Realistic scenario
*Describe a realistic scenario: what would happen from user perspective and what messages would be sent over the network?*


## 12. Reliability mechanisms
*The reliability mechanisms in your protocol (handling of network errors), if you have any*


## 13. Security mechanisms
*The security mechanisms in your protocol, if you have any*


## 14. Assumptions
*Assumptions if you made any*