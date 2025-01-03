import dataclasses


@dataclasses.dataclass
class Ad:
    title: str
    description: str
    price: float
    location: str

    def __str__(self):
        return f"{self.title} - {self.price} - {self.location}"
