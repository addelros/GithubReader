from githubreader import GithubReader

def main():
    # paths = ['opentap/opentap']
    myReader = GithubReader()
    # documents = myReader.load(paths=paths)
    # for document in documents:
    #     print("Document attributes:") 
        
    data = myReader.load_issues('opentap', 'opentap', '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')
    # for d in data: 
    #     print(d.text)
        
    print(data[340].text)

main()