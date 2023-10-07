class Field:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value


class BaseMessage:
    def __init__(self, title: str, description: str, fields: list[Field]):
        self.title = title
        self.description = description
        self.fields = fields
