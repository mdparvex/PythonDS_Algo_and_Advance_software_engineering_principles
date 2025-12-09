# import json

# path = "C:/Users/USER/Downloads/medicine_bulk.json"
# output_file = "C:/Users/USER/Downloads/output.txt"
# cleaned = []

# with open(path, "r", encoding="utf-8") as f:
#     for line in f:
#         line = line.strip()
#         if not line:
#             continue
        
#         obj = json.loads(line)
        
#         # Skip index lines
#         if "index" in obj:
#             continue
        
#         cleaned.append(obj)

# # Save cleaned JSON objects back to text (NDJSON format)
# with open(output_file, "w", encoding="utf-8") as f:
#     for obj in cleaned:
#         f.write(json.dumps(obj, ensure_ascii=False) +"," + "\n")

# print("Cleaning completed. Saved to:", output_file)

# import jwt
# import datetime

# import json
# import random

# input_file = "C:/Users/USER/Downloads/non_pharma.json"
# output_file = "C:/Users/USER/Downloads/updated_non_pharma.json"

# def update_documents():
#     # Load JSON
#     with open(input_file, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     updated = []

#     for doc in data:
#         # Add / generate title if missing or empty
#         if "title" not in doc or not doc["title"]:
#             doc["title"] = (
#                 doc.get("medicine_name", "") + " " +
#                 doc.get("strength", "") + " " +
#                 doc.get("category_name", "")
#             ).strip()

#         # Add random manufacturer_id if missing
#         if "manufacturer_id" not in doc:
#             doc["manufacturer_id"] = random.randint(1000, 9999)

#         # Add random order_count if missing
#         if "order_count" not in doc:
#             doc["order_count"] = random.randint(1000, 20000)

#         # Add is_show if missing
#         if "is_show" not in doc:
#             doc["is_show"] = True

#         updated.append(doc)

#     # Save updated JSON
#     with open(output_file, "w", encoding="utf-8") as f:
#         json.dump(updated, f, ensure_ascii=False, indent=4)

#     print(f"File saved as: {output_file}")

# if __name__ == "__main__":
#     update_documents()

import jwt
import datetime
import requests

SECRET ="1cvb+kq@@h5nnuxla%j&zj$1eq$@SDDm0&dk&y3tn$^^l%dejc&5#" #"8c71b51a5c552594c00ffdc129a613dd58b53745cbcdec5c9f26204585599eec178cbd177242546068fcfd827b001a0052e8a7b9cce0361aa1f2f490c0956721"

def generate_service_token():
    payload = {
        "service": "admin_service",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

token = generate_service_token()
print(token)
# res = requests.get(
#     "http://your-django-service/test/",
#     headers={"Authorization": f"Bearer {token}"}
# )

# print(res.json())

