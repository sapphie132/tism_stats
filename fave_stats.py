import math
import requests
import re
import sys
import json
import random

debug = False
page_limit = None

state_file = 'state.json'
try:
    with open(state_file, 'r') as f:
        print("Loading previous state…")
        print(f"If this step crashes, try removing the {state_file} file")
        obj = json.load(f)
        if "username" in obj:
            use_username = True
            username = obj['username']
        else:
            use_username = False
            user_id = obj['user_id']

        loaded_posts = obj['saved_posts']
        loaded_posts = {int(p_id):post for (p_id, post) in loaded_posts.items()}

except FileNotFoundError as e:
    obj = None
    loaded_posts = {}

if obj is None:
    if len(sys.argv) > 1 and sys.argv[1] == "--username":
        use_username = True
    else:
        use_username = False
    
    if use_username:
        username = input("Please input your username: ")
    else:
        user_id = int(input("Please input your user id: "))

extra_query_term = input("Please input the extra search term (e.g. \"twilight sparkle\" or \"appledash\") to cross-reference: ")
    

if use_username:
    forum_query = f"subject:*SFW*, author: {username}"
    fave_query = f"faved_by: {username}, safe"
else:
    forum_query = f"subject:*SFW*, user_id: {user_id}"
    fave_query = f"faved_by_id: {user_id}, safe"

image_query = fave_query + f", ({extra_query_term})"
filter_id = 2 # Everything*

booru = "https://ponybooru.org"


def save_state(posts_to_save):
    to_write = {'saved_posts': posts_to_save}
    if use_username:
        to_write['username'] = username
    else:
        to_write['user_id'] = user_id

    with open(state_file, 'w') as f:
        json.dump(to_write, f)

# base_results and interesting_attributes aren't mutated
def get_results(url_search, payload_key, page_limit, base_results = None, interesting_attributes = None):
    if interesting_attributes is None:
        interesting_attributes = []

    if base_results is None:
        base_results = {}

    def list_to_dict(l):
        res = {}
        for i in l:
            curr = {}
            for att in interesting_attributes:
                curr[att] = i[att]
            
            res[int(i['id'])] = curr

        return res

    resp = requests.get(url_search)
    if debug:
        print(url_search)
        print(resp)
    resp = resp.json()
    
    if debug:
        print(resp.keys())
    results = list_to_dict(resp[payload_key])
    total = resp["total"]
    if debug:
        print(len(results))
    print(f"Total: {total}")
    
    page = 2 # we just fetched page 1
    results = {**results, **base_results}
    while len(results) < total:
        if page_limit is not None and page > page_limit:
            break
        print(f"Fetching page {page}")
        url_search_page = url_search + f"&page={page}"
        # TODO: add better handling of possible fucky-wuckery
        resp = requests.get(url_search_page)
        if debug:
            print(resp)
        resp = resp.json()
        page += 1
        new_res = list_to_dict(resp[payload_key])
        if debug:
            print(len(new_res))

        results = {**results, **new_res}

    return results

def get_posts(page_limit = None, loaded_posts = None):
    loaded_posts = {} if loaded_posts is None else loaded_posts
    if random.random() < 0.05: # 5% chance to redownload the whole catalogue
        loaded_posts = {}
    base_url_search = "/api/v1/json/search/posts"
    url_search = booru + base_url_search + f"?q={forum_query}&per_page=50"
    print("Fetching forum posts…")
    posts = get_results(url_search, "posts", page_limit, loaded_posts, ["body"])
    return posts

def get_images(page_limit = None):
    url_search = get_img_search_url(image_query)
    print("Fetching images…")
    images = get_results(url_search, "images", page_limit)
    return images

def get_total_faves():
    url_search = get_img_search_url(fave_query)
    if debug:
        print(fave_query)
        print(url_search)
    resp = requests.get(url_search)
    resp = resp.json()
    #print(resp)
    return resp['total']

def get_img_search_url(query):
    base_url_search = "/api/v1/json/search/images"
    url_search = booru + base_url_search + f"?q={query}&filter_id={filter_id}&per_page=50"
    return url_search

def mk_post_url(p_id):
    return f"https://ponybooru.org/forums/dis/topics/post-a-random-sfw-image-from-your-favorites?post_id={p_id}#post_{p_id}"

def calc_prob(n, p, i):
    total = 0
    for j in range(i+1):
        curr = math.comb(n, j) * ((1-p) ** (n-j)) * (p ** j)
        if j == i:
            exact = curr
        else:
            total += curr

    return total, exact, 1-total-exact


posts = get_posts(page_limit, loaded_posts)
save_state(posts)
images = get_images(page_limit)

image_regex = re.compile(">>(\d+)")
post_images = {}
multiple_per_post = {}
for p_id in posts:
    post = posts[p_id]
    body = post["body"]
    matches = image_regex.findall(body)
    if len(matches) > 1:
        multiple_per_post[p_id] = matches
    
    if len(matches) > 0:
        post_images[p_id] = int(matches[0])


# Haven't tested this, hopefully it works as intended and doesn't
# crash the program
if len(multiple_per_post.keys()) > 0:
    print("Warning: some posts containing multiple images were found.")
    print("Only the first image of each of those posts was taken into account")
    print("Offending posts:")
    for p_id in multiple_per_post:
        imgs = multiple_per_post[p_id]
        print(mk_post_url(p_id) + f" ({', '.join(imgs)})")

# Converting to set for quicker lookup
fave_images = set(images.keys())
total_faves = get_total_faves()
overlap = 0

# Using a set for post_images wouldn't work
# because an image can occasionally be picked twice
# for the thread
print("\n====================================\n")
print("Posts containing the queried images:")
for p_id in post_images:
    img = post_images[p_id]
    if img in fave_images:
        overlap += 1
        print(mk_post_url(p_id))

p = len(fave_images) / total_faves 
expected_value = p * len(post_images)

print(f"Images in your (safe) favourites matching the query: {len(fave_images)}")
print(f"Total (safe) images in your faves: {total_faves}")
print(f"Posts (that contain at least one image) made in the thread: {len(post_images)}")
print(f"Images from this query that were posted to the thread: {overlap}")
print(f"Expected value: {expected_value:.1f}")
p_less, p_exact, p_more = calc_prob(len(post_images), p, overlap)
print(f"Probability of randomising exactly {overlap} images from this query: {p_exact:%}")
print(f"Probability of randomising less: {p_less:%}")
print(f"Probability of randomising more: {p_more:%}")
