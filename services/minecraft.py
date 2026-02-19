from mcstatus import JavaServer


class MinecraftService:
    """Service layer for minecraft server interaction"""
    def __init__(self, server_ip: str):
        self.server = JavaServer.lookup(server_ip)

    def get_status(self):
        return self.server.status()

    def ping(self):
        return self.server.ping()