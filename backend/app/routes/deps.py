"""Shared request dependencies: the app's database, memory and storage folder."""
from fastapi import Request


def get_conn(request: Request):
    return request.app.state.conn


def get_mem(request: Request):
    return request.app.state.mem


def get_storage(request: Request):
    return request.app.state.storage_dir
