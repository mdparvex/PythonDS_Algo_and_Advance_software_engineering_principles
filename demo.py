import json

path = "C:/Users/USER/Downloads/medicine_bulk.json"
output_file = "C:/Users/USER/Downloads/output.txt"
cleaned = []

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        obj = json.loads(line)
        
        # Skip index lines
        if "index" in obj:
            continue
        
        cleaned.append(obj)

# Save cleaned JSON objects back to text (NDJSON format)
with open(output_file, "w", encoding="utf-8") as f:
    for obj in cleaned:
        f.write(json.dumps(obj, ensure_ascii=False) +"," + "\n")

print("Cleaning completed. Saved to:", output_file)
