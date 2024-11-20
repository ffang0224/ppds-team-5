import requests
import json
from time import sleep

username = 'ab10028'
apiKey = 'ltEgVYG44NCRoABijfyEmFrfF'
scraper = 'instagramPost'
url = 'https://www.instagram.com/p/C-4eBD7KDYW/?igsh=MWljcnpuNWdrOXFtbg=='

apiEndPoint = "http://api.scraping-bot.io/scrape/data-scraper"
apiEndPointResponse = "http://api.scraping-bot.io/scrape/data-scraper-response?"

payload = json.dumps({"url": url, "scraper": scraper})
headers = {
    'Content-Type': "application/json"
}

response = requests.request("POST", apiEndPoint, data=payload, auth=(username, apiKey), headers=headers)
if response.status_code == 200:
    print(response.json())
    print(response.json()["responseId"])
    responseId = response.json()["responseId"]

    pending = True
    while pending:
        # sleep 5s between each loop, social-media scraping can take quite long to complete
        # so there is no point calling the api quickly as we will return an error if you do so
        sleep(5)
        finalResponse = requests.request("GET", apiEndPointResponse + "scraper=" + scraper + "&responseId=" + responseId
                                         , auth=(username, apiKey))
        result = finalResponse.json()
        if type(result) is list:
            pending = False
            print(finalResponse.text)
        elif type(result) is dict:
            if "status" in result and result["status"] == "pending":
                print(result["message"])
                continue
            elif result["error"] is not None:
                pending = False
                print(json.dumps(result, indent=4))

else:
    print(response.text)


# import requests
# import json
# from time import sleep

# username = 'ab10028'
# apiKey = 'ltEgVYG44NCRoABijfyEmFrfF'
# scraper = 'instagramProfile'
# # hashtag = '#nyceats'
# account = 'aru_bolatova'

# apiEndPoint = "http://api.scraping-bot.io/scrape/data-scraper"
# apiEndPointResponse = "http://api.scraping-bot.io/scrape/data-scraper-response?"

# payload = json.dumps({"account": account, "scraper": scraper})
# headers = {
#     'Content-Type': "application/json"
# }

# response = requests.request("POST", apiEndPoint, data=payload, auth=(username, apiKey), headers=headers)
# if response.status_code == 200:
#     print(response.json())
#     print(response.json()["responseId"])
#     responseId = response.json()["responseId"]

#     pending = True
#     while pending:
#         # sleep 5s between each loop, social-media scraping can take quite long to complete
#         # so there is no point calling the api quickly as we will return an error if you do so
#         sleep(5)
#         finalResponse = requests.request("GET", apiEndPointResponse + "scraper=" + scraper + "&responseId=" + responseId
#                                          , auth=(username, apiKey))
#         result = finalResponse.json()
#         if type(result) is list:
#             pending = False
#             print(finalResponse.text)
#         elif type(result) is dict:
#             if "status" in result and result["status"] == "pending":
#                 print(result["message"])
#                 continue
#             elif result["error"] is not None:
#                 pending = False
#                 print(json.dumps(result, indent=4))

# else:
#     print(response.text)


# import requests
# import json
# from time import sleep

# username = 'ab10028'
# apiKey = 'ltEgVYG44NCRoABijfyEmFrfF'
# scraper = 'instagramHashtag'
# hashtag = 'nyceats'

# apiEndPoint = "http://api.scraping-bot.io/scrape/data-scraper"
# apiEndPointResponse = "http://api.scraping-bot.io/scrape/data-scraper-response?"

# payload = json.dumps({"hashtag": hashtag, "scraper": scraper})
# headers = {
#     'Content-Type': "application/json"
# }

# response = requests.request("POST", apiEndPoint, data=payload, auth=(username, apiKey), headers=headers)
# if response.status_code == 200 or response.status_code == 202:
#     print(response.json())
#     print(response.json()["responseId"])
#     responseId = response.json()["responseId"]

#     pending = True
#     while pending:
#         # sleep 5s between each loop, social-media scraping can take quite long to complete
#         # so there is no point calling the api quickly as we will return an error if you do so
#         sleep(5)
#         finalResponse = requests.request("GET", apiEndPointResponse + "scraper=" + scraper + "&responseId=" + responseId
#                                          , auth=(username, apiKey))
#         result = finalResponse.json()
#         print(finalResponse)

#         if type(result) is list:
#             pending = False
#             print(finalResponse.text)
#         elif type(result) is dict:
#             if "status" in result and result["status"] == "pending":
#                 print(result)
#                 continue
#             elif result["error"] is not None:
#                 pending = False
#                 print(result)
#                 print(json.dumps(result, indent=4))

# else:
#     print(response)

