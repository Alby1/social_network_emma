import json
import time

import os

import dotenv

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

def parse_notifications(sess: str) -> tuple[bool, int]:
    r = request("POST", f"{BASE_URL}/api/get_notifications.php", params={
        "accessToken": sess
    })

    if (r.status_code != 200):
        print(f"ERROR parsing notifications.")
        return
    
    p = r.json()

    replied_to = 0

    for n in p:
        notification_id = n["id"]
        
        post_id = n["post_id"]
        
        content_key = n["content_key"]
        if (content_key in ['POST_MENTION', "POST_REPLIED"]):
            print(f"Working on notification {notification_id} for post {post_id}.")

            replied_to += 1

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
        
        return True, replied_to

    return False, 0
    
        

def login(username: str, password: str) -> str:
    r = request("POST", f"{BASE_URL}/api/login.php", data={
        "username": username,
        "password": password
    })
    
    token = None

    if (r.status_code == 200):
        print(f"Successfully logged in to {username}.")
        p = r.json()
        if (p["message"] in "loggedin"):
            token = p["access_token"]
    else:
        print(f"Could not log in to {username}: {p}.")
    
    return token


if __name__ == '__main__':
    try:
        dotenv.load_dotenv()

        main_sess = login('emma', os.getenv("PASSWORD"))

        logs_enabled: bool = False
        logs_sess: str | None = None

        replies = 0

        lp = os.getenv("LOGS_PASSWORD")
        if (lp):
            logs_enabled = True
        
        if (logs_enabled):
            logs_sess = login('emma_logs', lp)

        if (main_sess is not None):
            last_status_count = 1
            last_success: bool | None = None
            while True:
                success, replied_to = parse_notifications(main_sess)
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
                            reply_to(logs_sess, string, "624")

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
            reply_to(logs_sess, str(e), "624")
        
        print(str(e))
    
    exit(1)
