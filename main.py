import json
import time

import os

import dotenv

from requests import request
from requests.cookies import RequestsCookieJar, cookiejar_from_dict


BASE_URL = "http://thehardcoder.zapto.org/socialnetwork/"

def delete_notification(session_token: str, notification_id: str):
    reply = request("POST", f"{BASE_URL}/api/delete_notification.php", data={
        "accessToken": session_token,
        "notificationId": notification_id
    })

    if(reply.status_code == 200):
        print(f"Notification {notification_id} deleted.")
    else:
        print(f"ERROR Deleting notification {notification_id}.")


def get_post_content(session_token: str, post_id: str) -> str:
    reply = request("POST", f"{BASE_URL}/api/post_info.php", params={
        "accessToken": session_token,
        "postId": post_id
    })

    if (reply.status_code != 200):
        print(f"ERROR getting content from post {post_id}.")
        return
    
    payload = reply.json()

    print(f"Got content from post {post_id}.")

    return payload["content"]

def reply_to(session_token: str, content: str, post_id: str):
    reply = request("POST", f"{BASE_URL}/api/reply_post.php", data={
        "accessToken": session_token,
        "replyId": post_id,
        "content": content
    })

    if (reply.status_code != 200):
        print(f"ERROR replying to post {post_id}.")
        return
    
    print(f"Replied to post {post_id}.")

def parse_notifications(session_token: str) -> tuple[bool, int]:
    reply = request("POST", f"{BASE_URL}/api/get_notifications.php", params={
        "accessToken": session_token
    })

    if (reply.status_code != 200):
        print(f"ERROR parsing notifications.")
        return
    
    payload = reply.json()

    replied_to = 0

    for post in payload:
        notification_id = post["id"]
        
        post_id = post["post_id"]
        
        content_key = post["content_key"]
        if (content_key in ['POST_MENTION', "POST_REPLIED"]):
            print(f"Working on notification {notification_id} for post {post_id}.")

            replied_to += 1

            post_content = get_post_content(session_token, post_id)

            call = {
                "model": "emma",
                "messages": [
                    {"role": "user", "content": post_content}
                ]
            }
            
            emma_reply = request("POST", "https://remmake.it/api/v1/chat/completions", headers={"Content-Type": "application/json"}, data=json.dumps(call))

            if (emma_reply.status_code == 200):
                emma_payload = emma_reply.json()

                emma_content = emma_payload["choices"][0]["message"]["content"]

                print(f"Emma replied \"{emma_content}\" to \"{post_content}\".")

                reply_to(session_token, emma_content, post_id)

            else:
                print(f"Skipping notification {notification_id}, as it's of type {content_key}")

        delete_notification(session_token, notification_id)
        
        return True, replied_to

    return False, 0
    
        

def login(username: str, password: str) -> str:
    reply = request("POST", f"{BASE_URL}/api/login.php", data={
        "username": username,
        "password": password
    })
    
    token = None

    if (reply.status_code == 200):
        print(f"Successfully logged in to {username}.")
        payload = reply.json()
        if (payload["message"] in "loggedin"):
            token = payload["access_token"]
    else:
        print(f"Could not log in to {username}: {payload}.")
    
    return token


if __name__ == '__main__':
    logs_enabled: bool = False
    try:
        dotenv.load_dotenv()

        main_session_token = login('emma', os.getenv("PASSWORD"))

        logs_session_token: str | None = None

        replies = 0

        logs_password = os.getenv("LOGS_PASSWORD")
        if (logs_password):
            logs_enabled = True
        
        if (logs_enabled):
            logs_session_token = login('emma_logs', logs_password)

        if (main_session_token is not None):
            last_status_count = 1
            last_success: bool | None = None
            while True:
                success, replied_to = parse_notifications(main_session_token)
                replies += replied_to

                if (success != last_success):
                    if (last_success != None):
                        string = f"Status update:\n" \
                        f"Last status was {'successful' if last_success else 'unsuccessful'} for {last_status_count} iterations.\n" \
                        f"Current status is {'successful' if success else 'unsuccessful'}."

                        if (success == True):
                            string = f"{string}\nReplied to {replies} posts."

                        print(string)
                        
                        if (logs_enabled):
                            reply_to(logs_session_token, string, "624")

                    last_status_count = 1
                    last_success = success
                    replies = 0
                else:
                    last_status_count += 1


                time.sleep(5)
        else:
            print("Could not login.")
    except Exception as e:
        if(logs_enabled):
            reply_to(logs_session_token, str(e), "624")
        
        print(str(e))
    
    exit(1)
