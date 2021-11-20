import re
import requests
import json
import base64
from pathlib import Path
from typing import Union


def npj(v: dict):
    """
    Pretty prints a dict
    :param v: the dict
    :return:
    """
    print(json.dumps(v, indent=4))


def validate_path(path) -> str:
    """
    Fixes path e.g.  an empty path to ".",   "test\\test2" -> "test/test2"
    :param path:
    :return:
    """
    _out = "/".join(Path(path).parts)
    # If path is highest
    if not _out:
        _out = "."
    return _out


def is_sha(_input: str) -> bool:
    """
    Check if input is a sha by making sure all 40 letters are either alphabet or numbers
    """
    return len(_input) == 40 and re.findall("[0-9a-z]{40}", _input)


class Child:
    def __init__(self, info, base):
        """
        A private class used in Response.children main functions are
        .remove() -> deletes child
        .type -> file or directory
        .path
        .name
        .size
        .to_dict
        :param info: The information fetched from the api
        :param base: The database to be used in self.remove()
        """
        self.__info = info
        self.__base = base

    def remove(self):
        """
        Removes child from database
        """
        self.__base.remove(self.path)

    def to_dict(self) -> dict:
        """
        Returns a dictionary containing info of this
        """
        return {"path": self.path, "sha": self.sha, "name": self.name, "type": self.type, "size": self.size}

    @property
    def type(self):
        """
        Returns either 'file' or 'directory'
        """
        return 'file' if self.__info["type"] == "blob" else "directory"

    @property
    def path(self):
        """
        Path of child e.g. temp/test.json
        """
        return self.__info["path"]

    @property
    def size(self):
        """
        Size of file, it will return None if child is directory
        """
        return self.__info['size'] if self.type == 'file' else None

    @property
    def sha(self):
        """
        Returns SHA-HASH of child
        """
        return self.__info["sha"]

    @property
    def name(self):
        """
        Returns name of child without path e.g. temp.json
        """
        return Path(self.__info["path"]).name


class Response:
    def __init__(self, info: dict, headers: dict, base):
        """
        A class used in Database.get() function, it has several informative
        functions such as: content, json, text, remove, type, children, to_dict
        :param info: Information of blob/tree fetched from the api
        :param headers: Headers to be used in api call {"Authorization": "token ..."}
        :param base: The Database, used in Response.remove()
        """
        self.__info = info
        self.__headers = headers
        self.__base64 = ""
        self.__base = base
        self.__children = []

    def remove(self):
        """
        Removes file from database
        """
        self.__base.remove(self.path)

    def to_dict(self) -> dict:
        """
        Returns a dictionary containing info of this
        """
        return {"path": self.path, "sha": self.sha, "name": self.name, "type": self.type, "size": self.size}

    @property
    def path(self) -> str:
        """
        Returns path of response, e.g. temp/test.json
        """
        return self.__info["path"]

    @property
    def name(self) -> str:
        """
        Returns name of child without path e.g. temp.json
        """
        return Path(self.__info["path"]).name

    @property
    def type(self) -> str:
        """
        Returns type of Response, e.g. 'file' or 'directory'
        """
        return 'file' if self.__info["type"] == "blob" else "directory"

    @property
    def sha(self) -> str:
        """
        Returns SHA-HASH of response
        """
        return self.__info["sha"]

    @property
    def size(self) -> Union[int, None]:
        """
        Returns size in INT if the response is a file otherwise returns None
        """
        return self.__info["size"] if self.__info["type"] == "blob" else None

    def __get_base64(self):
        """
        Retrieves the base64 information from github
        """
        self.__base64 = requests.get(self.__info["url"], headers=self.__headers).json()["content"]

    def __check_for_base64(self):
        """
        Fetches base64 content if not already has
        """
        if not self.__base64:
            self.__get_base64()

    def __check_for_children(self):
        """
        Checks for children in the basement and uncles house ORR MAYBE JUST MAKES SURE
        WE CACHED CHILDREN OF THIS DIRECTORY JUST MAYBE
        """
        # Fetch if not fetched
        if not self.__children:
            self.__children = requests.get(self.__info["url"], headers=self.__headers).json()['tree']
            for i, ch in enumerate(self.__children):
                # It returns paths in local scope e.g. if response's path is test/test2
                # and you fetch children, raw data is file.json instead of test/test2/file.json
                # So well just fix it by adding the two paths and turning it from file\\file.txt to file/file.txt
                self.__children[i]['path'] = str(Path(self.__info['path']) / ch['path']).replace("\\", "/")

    def __is_tree(self) -> bool:
        """
        Is this a fucking directory?
        """
        return self.__info["type"] == "tree"

    @property
    def json(self) -> dict:
        """
        Gets content of response if it's a file in JSON|DICT type.
        e.g. db.get("file.json").json -> {"..": ...}
        If Response is directory it returns None
        """
        self.__check_for_base64()
        # base64 -> string bytes -> string -> dict              if file else None
        return json.loads(base64.b64decode(self.__base64).decode('utf-8')) if not self.__is_tree() else None

    @property
    def text(self) -> str:
        """
        Gets content of response if it's a file in STRING type.
        e.g. db.get("file.json").text -> "{\"..\": ...}"
        If Response is directory it returns None
        """
        self.__check_for_base64()
        # base64 -> string bytes -> string  if file else None
        return base64.b64decode(self.__base64).decode('utf-8') if not self.__is_tree() else None

    @property
    def content(self) -> bytes:
        """
        Gets content of response if it's a file in BYTES format, useful for image applications
        e.g. db.get("pic.jpg").content -> b'\34\5\b\3...'
        If Response is directory it returns None
        """
        self.__check_for_base64()
        return base64.decodebytes(self.__base64.encode('ascii')) if not self.__is_tree() else None

    @property
    def children(self) -> [Child]:
        """
        Returns Children of directory,
        e.g. db.get("path") -> [Child, Child]
        """
        self.__check_for_children()
        return [Child(x, self.__base) for x in self.__children] if self.__is_tree() else None


class Database:
    def __init__(self, token: str, name: str):
        """
        Declares a Github Database variable

        :param token: Github user token
        :param name: The name of the repo that
        will/is going to store the data. If it
        was not found it will create a private repo
        :rtype: Database
        """

        self._token = token
        self._name = name
        self.__cache = {}
        self._api = "https://api.github.com"

        # Get user info
        self._info = self._api_req("/user").json()
        if "id" not in self._info:
            raise Exception(json.dumps(self._info, indent=4))
        self._login = self._info["login"]

        # Check if repository exists otherwise make one
        self._repo = self._api_req(f"/repos/{self._login}/{self._name}").json()
        if "id" not in self._repo:
            # Set auto_init: True, to stop errors of empty repository, it basically creates README.md file
            self._repo = self._api_req("/user/repos",
                                       {"name": self._name, "private": True, "auto_init": True}, "post").json()
        else:
            # In-case of redirects/renames e.g. helpful2 -> helpful
            self._name = self._repo["name"]

        self._update_all_sha()

    def _update_all_sha(self):
        """
        Re caches all tree information
        :return:
        """
        self.__cache = self._api_req(f"/repos/{self._login}/{self._name}/git/trees/main?recursive=1").json()
        if "tree" not in self.__cache:
            self._create_readme()
            self._update_all_sha()

    def _create_readme(self):
        """
        Creates an empty readme, useful to activate empty repository
        """
        self._api_req(f"/repos/{self._login}/{self._name}/contents/README.md", {"message": "rm", "content": ""}, 'put')

    # Used to check if file exists in cache and if not it fetches it from github in the function below
    def _file_in_cache(self, path: str) -> Union[dict, None]:
        """
        Returns info if found in cache otherwise None
        :param path: path of file/directory
        """
        return next((item for item in self.__cache['tree'] if item['path'] == path), None)

    # Used in-case file wasn't found in cache,
    # Makes Get request for file in github
    # If response wasn't 404, it means file exists exist in cloud but not here,
    # So it updates all sha and returns from cache
    def _file_in_github(self, path: str) -> Union[dict, None]:
        if self._api_req(f"/repos/{self._login}/{self._name}/contents/{path}").status_code != 404:
            self._update_all_sha()
            return self._file_in_cache(path)
        return None

    def get(self, path: str) -> Union[Response, None]:
        """
        Give it a path or sha, and it'll return a Response if found
        else just None
        :param path: the PATH or SHA of the thing you want e.g.
        path: test/test.json
        sha:  f1a84e92cdfcdb32d2ebd94b015094e4d8b13c34
        """
        _path = validate_path(path)

        # If main directory was chosen
        if _path == ".":
            return Response(
                {"type": "tree", "path": ".", "sha": "main",
                 "url": f"{self._api}/repos/{self._login}/{self._name}/git/trees/main"}, self._get_headers(), self)

        if is_sha(_path):
            _path = self.__get_path_from_sha(_path)
            if not _path:
                # If A blob or tree was found in the cloud with matching sha then update cache
                if self._api_req(f"/repos/{self._login}/{self._name}/git/blobs/{path}").status_code != 404 or \
                        self._api_req(f"/repos/{self._login}/{self._name}/git/trees/{path}").status_code != 404:
                    self._update_all_sha()
                    _path = self.__get_path_from_sha(path)

        # Get the info from cache
        blob = self._file_in_cache(_path)
        if not blob:
            # If wasn't found in cache then get from github
            blob = self._file_in_github(_path)
        if not blob:
            # If not even found in github then return None
            return None

        # Finally deliver the response
        return Response(blob, self._get_headers(), self)

    def __upload_blob(self, _data) -> (str, int):
        """
        uploads blob to github and return sha and size
        :param _data:
        :return: Tuple(sha, size)
        """
        body = {
            "content": _data,
            "encoding": "base64"
        }
        # to avoid empty rep errors
        if not self.__cache['tree']:
            self._update_all_sha()

        # Upload the blob and get the sha
        sha = self._api_req(f"/repos/{self._login}/{self._name}/git/blobs", body, "post").json()['sha']
        # Retrieve the blob's size using the newly fetched sha, to be put in the cache
        size = self._api_req(f"/repos/{self._login}/{self._name}/git/blobs/{sha}").json()['size']
        return sha, size

    def __push_blob(self, path: str, blob_sha: str) -> str:
        """
        Push blob to main tree and retrieve SHA
        :param path: The path for the new blob
        :param blob_sha: The Sha of the blob
        :return: The hybrid tree sha
        """
        body = {
            "base_tree": "main",
            "tree": [
                {
                    "path": path,
                    # 100644 for files, 040000 for directories, 100755 for executables
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha
                }
            ]
        }
        return self._api_req(f"/repos/{self._login}/{self._name}/git/trees", body, "post").json()['sha']

    def set(self, path: str, value: Union[dict, str, bytes, list]):
        """
        Update a file with either a dict, string or bytes
        :param path: The path of the file to be updates
        :param value: This can be a DICT, STRING or BYTES (useful for images), Size should be lower than 100MB
        """

        _data = value
        if type(value) in [dict, list]:
            # pretty print the json to string format
            _data = json.dumps(value, indent=4)
        if type(value) != bytes:
            # if input wasn't in bytes format encode it into bytes, otherwise it would throw errors converting bytes to
            # bytes
            _data = _data.encode('ascii')

        # Encode into base64 and turn it to base64 string
        _data = base64.encodebytes(_data).decode('utf-8')

        # Upload and get sha
        blob_sha, blob_size = self.__upload_blob(_data)

        # Push blob to a main tree and get sha of new tree
        new_tree_sha = self.__push_blob(path, blob_sha)

        # Get last commit sha
        commit_sha = self.__cache["sha"] if "sha" in self.__cache else ""

        # Post new commit to github and get sha
        body = {
            "parents": [commit_sha],
            "tree": new_tree_sha,
            "message": "File update"
        }
        new_commit_sha = self._api_req(f"/repos/{self._login}/{self._name}/git/commits", body, "post").json()['sha']

        # Set new commit as the main commit
        body = {
            "sha": new_commit_sha
        }
        self._api_req(f"/repos/{self._login}/{self._name}/git/refs/heads/main", body, "post")

        # self._update_all_sha()
        # Update commit sha in cache
        self.__cache['sha'] = new_commit_sha

        # Manually create blob info and store iit in cache
        blob_info = {
            "path": path,
            "mode": "100644",
            "type": "blob",
            "size": blob_size,
            "sha": blob_sha,
            "url": f"{self._api}/repos/{self._login}/{self._name}/git/blobs/{blob_sha}"
        }
        self._replace_or_add_info_to_cache_tree(blob_info)

        # Update parents to avoid fetching old data
        self._update_parent_tree(path)

    # Updates all parents of a given path, because once a file changes in git
    # The whole goddamn parents ids change
    def _update_parent_tree(self, path):
        # Parents -> [Path(path/path)] -> [path\\path] -> [path/path]
        blob_parents = [str(x).replace("\\", "/") for x in list(Path(path).parents)]
        # To be used in known if last parent was reached in the loop below
        num_parents = len(blob_parents)
        # Reverse the list to start from the deepest parent and go higher
        blob_parents.reverse()
        for _i, _parent in enumerate(blob_parents):
            if _i != num_parents - 1:
                # Get children of parent1 to obtain new sha of parent2  e.g.  test/test2 (test1 is parent1)
                _sub_tree = self._get_tree_from_github(_parent, self._get_sha(_parent))
                _lower_parent = next((x for x in _sub_tree if x['path'] == blob_parents[_i + 1]), None)
                self._replace_or_add_info_to_cache_tree(_lower_parent)

    # The name says it all
    def _replace_or_add_info_to_cache_tree(self, info):
        _ind = next((index for (index, d) in enumerate(self.__cache['tree']) if d["path"] == info['path']), None)
        if _ind is not None:
            self.__cache['tree'][_ind] = info
        else:
            self.__cache['tree'].append(info)

    def _all_cache_paths(self) -> [str]:
        """
        Returns a list of all paths stored in cache
        """
        return [x['path'] for x in self.__cache['tree']]

    def _get_sha(self, path) -> str:
        """
        Returns the sha of the path if found otherwise None
        :param path:
        :return:
        """
        _path = validate_path(path)
        if _path == ".":
            return "main"
        _lis = (item['sha'] for item in self.__cache['tree'] if item["path"] == _path)
        return next(_lis, None)

    def remove(self, path: str):
        """
        Removes a given file or directory
        :param path: The path to delete
        """
        _path = validate_path(path)
        item = self.get(_path)
        # get the item information
        if item.type == "file":
            self._remove_from_github(item.path, item.sha)
            self._remove_from_cache(item.path)

        # If directory was given then just fucking delete every file inside
        else:
            # 1) Getting the children
            items = self._get_tree_from_github(item.path, item.sha, True)
            # 2) Fucking the children
            for _item in items:
                # Make sure its  file before sending an api call of deletion
                if _item["type"] == 'blob':
                    self._remove_from_github(_item["path"], _item["sha"])
                # Then delete it whether it was  directory or file from cache
                self._remove_from_cache(_item['path'])

            # 3) Fuck the directory itself but make sure its not the main directory
            if _path != ".":
                self._remove_from_cache(item.path)

        # Make sure the the parents forget everything that happened
        self._update_parent_tree(item.path)

    def _remove_from_github(self, path, sha):
        return self._api_req(f'/repos/{self._login}/{self._name}/contents/{path}',
                             {"message": "Removed File", "sha": sha}, "delete").json()

    def _remove_from_cache(self, path):
        i, item = next(((i, item) for (i, item) in enumerate(self.__cache['tree']) if item["path"] == path), None)
        if item:
            del self.__cache['tree'][i]
        else:
            print(f"Item {path} was not found")

    def _get_tree_from_github(self, path: str, sha: str, recursive=False) -> [dict]:
        """
        Gets children of a tree
        :param path: The Path of the tree (to be used in mixing the child and parent path)
        :param sha: The sha of the tree
        :param recursive: Get everything inside the tree?
        :return:
        """
        uri = f"/repos/{self._login}/{self._name}/git/trees/{sha}{'?recursive=1' if recursive else ''}"
        _tree = self._api_req(uri).json()['tree']
        for i, item in enumerate(_tree):
            # Fix the paths
            _tree[i]['path'] = str(Path(path) / item['path']).replace("\\", "/")
        return _tree

    def _api_req(self, uri: str, body: dict = None, method: str = "get") -> requests.Response:
        """
        Calls a request
        :param uri: Url of the request e.g "/user"
        :param body: Body of the request if not get method
        :param method: The method of request ["get", "post"]
        :return: requests.Response class
        """
        return requests.request(method.upper(), f"{self._api}{uri}", json=body, headers=self._get_headers())

    def __get_path_from_sha(self, sha: str):
        """
        Self explanatory, finds path of a given sha
        """
        for _i in self.__cache['tree']:
            if _i['sha'] == sha:
                return _i['path']
        return None

    def _get_headers(self):
        return {"Authorization": f"token {self._token}"}


# if __name__ == "__main__":
#     # GET YOUR GITHUB TOKEN, MAKE SURE U HAVE "REPO" PERMS
#     # https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
#     # if given repository didn't exist, it'll make one automatically
#     db = Database("GITHUB_TOKEN", "REPO_NAME")

#     # 1. Creating a text file and getting it
#     db.set("hello_world.txt", "Hello world!")
#     print(db.get("hello_world.txt").text)

#     # 2. Creating a json file and getting it
#     db.set("hello_world2.json", {"hello": "world"})
#     print(db.get("hello_world2.json").json)

#     # 3. Uploading an image and getting it
#     from PIL import Image
#     from io import BytesIO
#     image_url = "https://freepngimg.com/save/13358-happy-person-free-download-png/275-261"
#     image_bytes = requests.get(image_url).content
#     # Uploading..
#     db.set("image.png", image_bytes)
#     # Retrieving the bytes again
#     image_bytes_from_github = db.get("image.png").content
#     # Displaying it
#     Image.open(BytesIO(image_bytes_from_github)).show()

#     # 4. Getting children of directory
#     children = db.get(".").children
#     for child in children:
#         print("Sha:", child.sha, "Path:", child.path)

#     # 5. Response object to dict
#     print(db.get("hello_world.txt").to_dict())

#     # 6. Deleting/Removing a file or directory
#     db.remove("hello_world.txt")

#     # 7. Deleting everything
#     db.remove(".")
