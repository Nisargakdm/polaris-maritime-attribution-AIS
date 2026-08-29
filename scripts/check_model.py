import torch
checkpoint = torch.load("data/models/model.pth", map_location="cpu", weights_only=False)
print("Checkpoint keys:", list(checkpoint.keys()) if isinstance(checkpoint, dict) else "Not a dict")
print("Type:", type(checkpoint))
