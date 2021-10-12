url = "/path/12/s/30"

urls = "/path/{id}/s/{otoid}"

list = url.split("/")
lists = urls.split("/")

params = {}

i = 0
for item in lists:
    if item:
        if item[0] == '{' and item[len(item)-1] == '}':
            auxItem = item.strip("{}")
            params[auxItem] = list[i]
    i += 1

print(params)

