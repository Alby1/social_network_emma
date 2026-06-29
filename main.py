import json
import time

import os

from requests import request
from requests.cookies import RequestsCookieJar, cookiejar_from_dict


BASE_URL = "http://thehardcoder.zapto.org/socialnetwork/"

def delete_notification(sess: str, notification_id: str):
    r = request("POST", f"{BASE_URL}/api/delete_notification.php", data={
        "accessToken": sess,
        "notificationId": notification_id
    })

    if(r.status_code == 200):
        print(f"Notification {notification_id} deleted.")
    else:
        print(f"ERROR Deleting notification {notification_id}.")


def get_post_content(sess: str, post_id: str) -> str:
    r = request("POST", f"{BASE_URL}/api/post_info.php", params={
        "accessToken": sess,
        "postId": post_id
    })

    if (r.status_code != 200):
        print(f"ERROR getting content from post {post_id}.")
        return
    
    p = r.json()

    print(f"Got content from post {post_id}.")

    return p["content"]

def reply_to(sess: str, content: str, post_id: str):
    r = request("POST", f"{BASE_URL}/api/reply_post.php", data={
        "accessToken": sess,
        "replyId": post_id,
        "content": content
    })

    if (r.status_code != 200):
        print(f"ERROR replying to post {post_id}.")
        return
    
    print(f"Replied to post {post_id}.")

def parse_notifications(sess: str):
    r = request("POST", f"{BASE_URL}/api/get_notifications.php", params={
        "accessToken": sess
    })

    if (r.status_code != 200):
        print(f"ERROR parsing notifications.")
        return
    
    print(f"Read notifications.")
    p = r.json()

    for n in p:
        notification_id = n["id"]
        
        post_id = n["post_id"]
        
        content_key = n["content_key"]
        if (content_key in ['POST_MENTION', "POST_REPLIED"]):
            print(f"Working on notification {notification_id} for post {post_id}.")

            c = get_post_content(sess, post_id)

            call = {
                "model": "emma",
                "messages": [
                    {"role": "user", "content": c}
                ]
            }
            
            r_ai = request("POST", "https://remmake.it/api/v1/chat/completions", headers={"Content-Type": "application/json"}, data=json.dumps(call))

            if (r_ai.status_code == 200):
                p_ai = r_ai.json()

                c_ai = p_ai["choices"][0]["message"]["content"]

                print(f"Emma replied \"{c_ai}\" to \"{c}\".")

                reply_to(sess, c_ai, post_id)

            else:
                print(f"Skipping notification {notification_id}, as it's of type {content_key}")

        delete_notification(sess, notification_id)
        

def login() -> str:
    r = request("POST", f"{BASE_URL}/api/login.php", data={
        "username": 'emma',
        "password": os.getenv("PASSWORD")
    })
    
    token = None

    if (r.status_code == 200):
        print("Successfully logged in.")
        p = r.json()
        if (p["message"] in "loggedin"):
            token = p["access_token"]
    
    return token


if __name__ == '__main__':
    sess = login()

    if (sess is not None):
        while True:
            parse_notifications(sess)
            time.sleep(5)
    else:
        print("Could not login.")
    
    exit(1)
