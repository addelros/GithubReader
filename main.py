from githubreader import GithubReader

def main():
    paths = ['opentap/opentap']
    myReader = GithubReader()
    documents = myReader.load(paths=paths)
    for document in documents:
        print("Document attributes:") 

main()