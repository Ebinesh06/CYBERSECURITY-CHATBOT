import requests
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Connect to your existing ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="cyber_intelligence")

def ingest_cisa_kev():
    print("Fetching live data from CISA...")
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    response = requests.get(url)
    data = response.json()
    
    vulnerabilities = data.get("vulnerabilities", [])
    
    # 2. Use Professional Chunking
    # We use RecursiveCharacterTextSplitter to keep sentences together
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )

    print(f"Processing {len(vulnerabilities)} vulnerabilities...")
    
    for vuln in vulnerabilities[:100]:  # Let's start with the top 100 for speed
        content = f"CVE ID: {vuln['cveID']}\nVendor: {vuln['vendorProject']}\nProduct: {vuln['product']}\nDescription: {vuln['shortDescription']}\nRemediation: {vuln['requiredAction']}"
        
        # Metadata is the 'pro' way to filter searches later
        metadata = {
            "source": "CISA KEV",
            "cve_id": vuln['cveID'],
            "vendor": vuln['vendorProject']
        }
        
        chunks = text_splitter.split_text(content)
        
        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                metadatas=[metadata],
                ids=[f"{vuln['cveID']}_{i}"]
            )
    
    print("Successfully updated database with high-level threat intel!")

if __name__ == "__main__":
    ingest_cisa_kev()