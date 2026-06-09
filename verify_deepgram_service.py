from app.services import get_deepgram_audio_service

def main():
    print("Fetching service instance via dependency...")
    service1 = get_deepgram_audio_service()
    
    print("Fetching service instance via dependency again...")
    service2 = get_deepgram_audio_service()
    
    # Check if they are the same cached instance
    is_cached = (service1 is service2)
    print(f"Are the instances identical (cached)? {is_cached}")
    assert is_cached, "Failed: instances should be cached and identical"
    print("Dependency cache verification successful!")

if __name__ == "__main__":
    main()
