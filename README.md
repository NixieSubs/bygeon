# bygeon


![GitHub](https://img.shields.io/github/license/dummyx/bygeon)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bygeon)
![PyPI](https://img.shields.io/pypi/v/bygeon)

A simple tool for syncing messages between multiple IMs.

# Installation
It is recommended to use pipx to install bygeon.

```
pipx install bygeon
```

Python 3.10 or higher is required.

# Configuration

## Configuration file

The configuration file should be named bygeon.toml and placed in the working directory.

An [example](https://github.com/dummyx/bygeon/blob/main/bygeon.example.toml) is provided in the project.

## Slack

NOTE: Slack support is kind of broken now, use with caution.

Because bygeon is using WebSocket to receive events, app-level token is required alongside the normal bot token.

For more information, refer to [Slack's documentation](https://api.slack.com/apis/connections/socket).

## CQHttp

A running [go-cqhttp](https://github.com/Mrs4s/go-cqhttp) instance is needed to enable CQHttp. Make sure to enable WebSocket and HTTP in go-cqhttp's configuration and configure bygeon accordingly.

For how to setup go-cqhttp, refer to [their documentation](https://docs.go-cqhttp.org).
