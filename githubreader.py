import base64
import json
import os
from datetime import datetime

import requests
from wasabi import msg 

# from goldenverba.components.reader.document import Document
# from goldenverba.components.reader.interface import InputForm, Reader
from document import Document
from interface import InputForm, Reader


class GithubReader(Reader):
    """
    The GithubReader downloads files from Github and ingests them into Weaviate.
    """

    def __init__(self):
        super().__init__()
        self.name = "GithubReader"
        self.requires_env = ["GITHUB_TOKEN"]
        self.description = "Downloads only text files from a GitHub repository and ingests it into Verba. Use this format {owner}/{repo}/{branch}/{folder}"
        self.input_form = InputForm.INPUT.value

    def load(
        self,
        bytes: list[str] = None,
        contents: list[str] = None,
        paths: list[str] = None,
        fileNames: list[str] = None,
        document_type: str = "Documentation",
    ) -> list[Document]:
        """Ingest data into Weaviate
        @parameter: bytes : list[str] - List of bytes
        @parameter: contents : list[str] - List of string content
        @parameter: paths : list[str] - List of paths to files
        @parameter: fileNames : list[str] - List of file names
        @parameter: document_type : str - Document type
        @returns list[Document] - Lists of documents.
        """
        if fileNames is None:
            fileNames = []
        if paths is None:
            paths = []
        if contents is None:
            contents = []
        if bytes is None:
            bytes = []
        documents = []

        # If paths exist
        if len(paths) > 0:
            for path in paths:
                if path != "":
                    files = self.fetch_docs(path)

                    for _file in files:
                        try:
                            content, link, _path = self.download_file(path, _file)
                        except Exception as e:
                            msg.warn(f"Couldn't load, skipping {_file}: {str(e)}")
                            continue

                        if ".json" in _file:
                            print(content)
                            documents.append(json.loads(str(content)))
                            json_obj = json.loads(str(content))
                            try:
                                document = Document.from_json(json_obj)
                            except Exception as e:
                                raise Exception(f"Loading JSON failed {e}")

                        else:
                            document = Document(
                                text=content,
                                type=document_type,
                                name=_file,
                                link=link,
                                path=_path,
                                timestamp=str(
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                ),
                                reader=self.name,
                            )
                            print("Document attributes:")
                            print(f"Type: {document.type}")
                            print(f"Name: {document.name}")
                            print(f"Link: {document.link}")
                            print(f"Path: {document.path}")
                            print(f"Timestamp: {document.timestamp}")
                            print(f"Reader: {document.reader}")
                            print(f"Text: {document.text}") 
                            print("\n")
                        documents.append(document)

        msg.good(f"Loaded {len(documents)} documents")
        return documents

    def fetch_docs(self, path: str) -> list:
        """Fetch filenames from Github
        @parameter path : str - Path to a GitHub repository
        @returns list - List of document names.
        """
        split = path.split("/")
        owner = split[0]
        repo = split[1]
        branch = split[2] if len(split) > 2 else "main"
        folder_path = "/".join(split[3:]) if len(split) > 3 else ""

        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        headers = {
            "Authorization": "token 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",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        files = [
            item["path"]
            for item in response.json()["tree"]
            if item["path"].startswith(folder_path)
            and (
                item["path"].endswith(".cs")
                # or item["path"].endswith(".mdx")
                # or item["path"].endswith(".txt")
                # or item["path"].endswith(".json")
            )
        ]
        msg.info(
            f"Fetched {len(files)} filenames from {url} (checking folder {folder_path})"
        )
        return files

    def fetch_issues(self, owner: str, repo: str, token: str) -> list[dict]:
        """Fetch issues from GitHub repository.
        
        :param owner: str - Owner of the GitHub repository.
        :param repo: str - Name of the GitHub repository.
        :param token: str - GitHub token for authentication.
        :return: List[Dict] - List of issues.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        issues = []
        page = 1
        while True:
            params = {"page": page, "per_page": 100}  # Fetch 100 issues per page
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            issues_page = response.json()
            issues.extend(issues_page)
            if len(issues_page) < 100:
                break  # Break loop if less than 100 items returned (reached end of pages)
            page += 1
        return issues


    def load_issues(self, owner: str, repo: str, token: str, document_type: str = "Issue") -> list[Document]:
        """Ingest issues from GitHub repository into Weaviate.

        :param owner: str - Owner of the GitHub repository.
        :param repo: str - Name of the GitHub repository.
        :param token: str - GitHub token for authentication.
        :param document_type: str - Document type for issues.
        :return: List[Document] - List of documents.
        """
        issues = self.fetch_issues(owner, repo, token)
        documents = []

        for issue in issues:
            issue_title = issue["title"]
            issue_body = issue["body"]
            issue_link = issue["html_url"]
            # You can customize how you want to ingest the issue data into documents
            document = Document(
                text=f"Title: {issue_title}\nBody: {issue_body}",
                type=document_type,
                name=issue_title,
                link=issue_link,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                reader=self.name
            )
            documents.append(document)

        msg.good(f"Loaded {len(documents)} issues")
        return documents

    def download_file(self, path: str, file_path: str) -> str:
        """Download files from Github based on filename
        @parameter path : str - Path to a GitHub repository
        @parameter file_path : str - Path of the file in repo
        @returns str - Content of the file.
        """
        split = path.split("/")
        owner = split[0]
        repo = split[1]
        branch = split[2] if len(split) > 2 else "main"

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        headers = {
            "Authorization": "token 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",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        content_b64 = response.json()["content"]
        link = response.json()["html_url"]
        path = response.json()["path"]
        content = base64.b64decode(content_b64).decode("utf-8")
        msg.info(f"Downloaded {url}")
        return (content, link, path)
