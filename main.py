from fastapi import FastAPI, Request , Form, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel,Field
from google.cloud import firestore , storage
from uuid import uuid4
from typing import List, Optional
from fastapi import HTTPException , status ,APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
from google.auth.transport import requests
import google.oauth2.id_token
import time
import starlette.status as status
import local_constants
import uuid
from datetime import datetime

app = FastAPI()

# Serve static files like CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set template directory
templates = Jinja2Templates(directory="htmlpages")

firebase_db = firestore.Client()
firebase_request_adapter = requests.Request()


class Follower(BaseModel):
    username: str

class Following(BaseModel):
    username: str

class Comment(BaseModel):
    username: str
    comment: str
    time: str 

class Post(BaseModel):
    post_id: str
    Username: str             
    Date: str                 
    filename: str
    likes: int
    description: str
    comments: Optional[List[Comment]] = []

class User(BaseModel):
    name: str
    Username: str
    followers: Optional[List[Follower]] = []
    following: Optional[List[Following]] = []
    posts: Optional[List[str]] = []  
    joinedDate:str


class EmailRequest(BaseModel):
    username: str
 

class UsernameRequest(BaseModel):
    username: str
    name:str
    email:str


class FollowRequest(BaseModel):
    current_user: str 
    friendName:str
    currentuserprofilename:str
 

def createPost(filename, user, postdescription):
    post_id = str(uuid.uuid4())  # generate unique post ID
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # format current time
    firebase_db.collection('Post').add({
                "post_id": post_id,
                "Username": user['Username'],  
                "email":user['email'],        
                "Date": current_time,            
                "filename": filename,
                "likes": 0,
                "description": postdescription,
                "comments":[]
            })
    print("post ",{
                "post_id": post_id,
                "Username": user['Username'],  
                "email":user['email'],        
                "Date": current_time,            
                "filename": filename,
                "likes": 0,
                "description": postdescription,
                "comments":[]
            })


def getUserPosts(username):
    posts = []
    posts_ref = firebase_db.collection('Post')
    query = posts_ref.where('Username', '==', username).stream()
    for post in query:
        posts.append(post.to_dict())

    return posts



def addDirectory(directory_name):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(directory_name)
    blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')

def addFile(file , user , postdescription):
    print("inside add file")
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    # print(file)
    blob = storage.Blob(file.filename, bucket)
    blob.upload_from_file(file.file)
    createPost(file.filename,user, postdescription)

def blobList(prefix):
    print("local_constants.PROJECT_NAME ",local_constants.PROJECT_NAME)
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    return storage_client.list_blobs(local_constants.PROJECT_STORAGE_BUCKET, prefix=prefix)

def downloadBlob(filename):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.get_blob(filename)
    return blob.download_as_bytes()
    
def getuser(user_token):
    print("inside get user function")
    user = firebase_db.collection("users").document(user_token['user_id'])
    if not user.get().exists:
        user_data = {
            'name':'John Doe'
        }
        firebase_db.collection('users').document(user_token['user_id']).set(user_data)

    return user

def validateFirebaseToken(id_token):
    if not id_token:
        return None
    user_token = None 
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
    except ValueError as e:
        print(str(e))

    return user_token

def getuserfromemail(email):
    user_ref = firebase_db.collection('users').where('email', '==', email).limit(1).get()
    user_data = {
            'name':'John Doe'
        }
    if not user_ref:
        return user_data
    else:
        user_data = user_ref[0].to_dict()
        return user_data

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    id_token = request.cookies.get('token')
    error_message = "No error here"
    user_token = None
    user = None

    print("inside get")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse("main-page.html",{'request':request, 'user_token':None , 'error_message':None , 'user_info':None})
    
    print("user validated")
    file_list = []
    directory_list = []

    blobs = blobList(None)
    print("after blobs")
    for blob in blobs:
        if blob.name[-1] == "/":
            directory_list.append(blob)
        else:
            file_list.append(blob)
    print("after blob") 
    user = getuser(user_token).get()
    return templates.TemplateResponse("main-page.html", {"request": request, 'user_token':user_token , 'error_message':error_message , 'user_info':user, 'file_list':file_list,'directory_list':directory_list})

@app.get("/dashboard", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/test", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/testing", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("testing.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/userprofile/{username}", response_class=HTMLResponse)
async def renderuserprofile(request: Request, username:str):
    print("username ",username)
    return templates.TemplateResponse("userprofile.html", {"request": request, 'username':username})



@app.get("/followers", response_class=HTMLResponse)
async def renderfollowers(request: Request):
    id_token = request.cookies.get('token')
    error_message = "No error here"
    user_token = None
    user = None

    print("inside get")
    user_token = validateFirebaseToken(id_token)
    print("inside user toekn ",user_token)

    if not user_token:
        return templates.TemplateResponse("main-page.html",{'request':request, 'user_token':None , 'error_message':None , 'user_info':None})
    
    return templates.TemplateResponse("followers.html", {"request": request , 'user_email':user_token['email']})

@app.get("/following", response_class=HTMLResponse)
async def renderfollowing(request: Request):
    id_token = request.cookies.get('token')
    error_message = "No error here"
    user_token = None
    user = None

    user_token = validateFirebaseToken(id_token)

    print("inside user toekn ",user_token)
    if not user_token:
        return templates.TemplateResponse("main-page.html",{'request':request, 'user_token':None , 'error_message':None , 'user_info':None})
    
    return templates.TemplateResponse("following.html", {"request": request , 'user_email':user_token['email']})


@app.post("/checkandcreateuser")
async def checkandcreatenewuser(data: EmailRequest):
    # print("check user ", data)
    user_ref = firebase_db.collection('users').where('email', '==', data.username).limit(1).get()
    if not user_ref:
        firebase_db.collection('users').add({
                "name": "",
                "email":data.username,
                "joinedDate":time.strftime("%Y-%m-%dT%H:%M:%SZ",  time.gmtime()),
                "Username":"",
                "followers":[],
                "following":[],
                "posts":[]
            })
        print("user created")
    else:
        print("user already exist")
        pass
    return 0


@app.post("/getUser")
async def getUser(data: EmailRequest , response_class=JSONResponse):
    print("getting usrr")
    user_ref = firebase_db.collection('users').where('email', '==', data.username).limit(1).get()
    if not user_ref:
        return JSONResponse(content={"error": "User not found"}, status_code=404)
    else:
        user_data = user_ref[0].to_dict()
        return JSONResponse(content={"user": user_data}, status_code=200)

@app.post("/getUserUsingUsername")
async def getUser(data: EmailRequest , response_class=JSONResponse):
    print("getting usrr")
    user_ref = firebase_db.collection('users').where('Username', '==', data.username).limit(1).get()
    if not user_ref:
        return JSONResponse(content={"error": "User not found"}, status_code=404)
    else:
        user_data = user_ref[0].to_dict()
        return JSONResponse(content={"user": user_data}, status_code=200)

@app.post("/getPostsOfUser")
async def getPostsOfUser(data: EmailRequest, response_class=JSONResponse):
    print("getting posts of user")
    posts_ref = firebase_db.collection('Post').where('email', '==', data.username).get()
    if not posts_ref:
        posts = []
    else:
        posts = [doc.to_dict() for doc in posts_ref]
    return JSONResponse(content={"posts": posts}, status_code=200)

