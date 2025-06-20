import streamlit as st
import requests
from streamlit_extras.colored_header import colored_header
import base64
from Frontend import add_custom_css
from pymongo.errors import DuplicateKeyError
import streamlit as st
import requests
import json
from datetime import datetime
from difflib import SequenceMatcher
from streamlit_extras.add_vertical_space import add_vertical_space
import requests
import os
from PIL import Image, ImageDraw, ImageFont
import io
import hashlib
import random

# --- EMBEDDED API KEYS ---
HYPERCLOVA_API_KEY = "nv-270db94eb8bf42108110b22f551e655axCwf"
LIBRARY_API_KEY = "70b5336f9e785c681d5ff58906e6416124f80f59faa834164d297dcd8db63036"

# --- Load JSON files ---
@st.cache_resource
def load_dtl_kdc_json():
    """Load only the detailed KDC JSON file"""
    with open("dtl_kdc.json", encoding="utf-8") as f:
        dtl_kdc_dict = json.load(f)
    return dtl_kdc_dict

dtl_kdc_dict = load_dtl_kdc_json()

def display_liked_book_card(book, index):
    """Display a clean liked book card with minimal styling (no card container)."""
    info = book if isinstance(book, dict) else book.get("doc", {})
    
    # Extract book information
    title = info.get('bookname') or info.get('bookName', '제목 없음')
    authors = info.get('authors') or info.get('author', '저자 없음')
    publisher = info.get('publisher', '출판사 없음')
    year = info.get('publication_year') or info.get('publicationYear', '연도 없음')
    loan_count = info.get('loan_count') or info.get('loanCount', 0)
    isbn13 = info.get('isbn13') or info.get('isbn', 'unknown')
    current_category = info.get('category', 'To Read')
    image_url = info.get("bookImageURL", "")
    
    # Define category colors
    category_colors = {
        "To Read": "#ff6b6b",      # Red
        "Currently Reading": "#4ecdc4",  # Teal
        "Finished": "#45b7d1"      # Blue
    }
    
    # Category badge with colored background
    st.markdown(f"""
    <div style="
        text-align: right;
        margin-bottom: 5px;
    ">
        <span style="
            background: {category_colors.get(current_category, '#007bff')};
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.75em;
            font-weight: 600;
        ">
            {current_category}
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Content layout
    cols = st.columns([1, 3])
    
    with cols[0]:
        # Book image
        if image_url:
            st.image(image_url, width=120)
        else:
            st.markdown(f"""
            <div style="
                width: 120px;
                height: 160px;
                background: #f0f0f0;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
                margin: 0;
            ">
                📚 No Image
            </div>
            """, unsafe_allow_html=True)
    
    with cols[1]:
        # Book details with reduced spacing
        st.markdown(f"""
        <div style="margin-top: 0;">
            <h3 style="margin: 0 0 5px 0; color: #333;">{title}</h3>
            <p style="margin: 2px 0;"><strong>Author:</strong> {authors}</p>
            <p style="margin: 2px 0;"><strong>Publisher:</strong> {publisher}</p>
            <p style="margin: 2px 0;"><strong>Year:</strong> {year}</p>
            <p style="margin: 2px 0 10px 0;"><strong>Loan Count:</strong> {loan_count}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons - properly aligned
        btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 1])
        
        with btn_col1:
            if st.button("Tell me more", key=f"details_liked_{isbn13}_{index}"):
                st.session_state.selected_book = info
                st.session_state.app_stage = "discuss_book"
                st.rerun()
        
        with btn_col2:
            new_category = st.selectbox(
                "જ⁀➴       Status:", 
                ["To Read", "Currently Reading", "Finished"],
                index=["To Read", "Currently Reading", "Finished"].index(current_category),
                key=f"category_select_{isbn13}_{index}"
            )
            
            # Update category if changed
            if new_category != current_category:
                if hasattr(st.session_state, 'username') and st.session_state.username:
                    success = update_book_category(st.session_state.username, isbn13, new_category)
                    if success:
                        st.success("Status updated!")
                        st.rerun()
                    else:
                        st.error("Update failed")
        
        with btn_col3:
            if st.button("🗑️", key=f"remove_{isbn13}_{index}", help="Remove"):
                if hasattr(st.session_state, 'username') and st.session_state.username:
                    unlike_book_for_user(st.session_state.username, isbn13)
                    st.success("Removed from library!")
                    st.rerun()
    
    # Add a subtle separator between cards
    st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
        
# Add after MongoDB client initialization
def get_user_library_collection():
    client = st.session_state.db_client  # Already set in login.py
    db = client["Login_Credentials"]
    return db["user_libraries"]

def like_book_for_user(username, book_info, category="To Read"):
    user_library = get_user_library_collection()
    isbn = book_info.get("isbn13") or book_info.get("isbn")
    if not isbn:
        return False
    
    # Add category to book_info before saving
    book_with_category = book_info.copy()
    book_with_category["category"] = category
    book_with_category["date_added"] = datetime.now().isoformat()  # Track when book was added
    
    # First, try to add to existing document
    result = user_library.update_one(
        {"username": username},
        {"$addToSet": {"liked_books": book_with_category}}
    )
    
    # If no document was modified, create one with an empty array and add the book
    if result.matched_count == 0:
        user_library.update_one(
            {"username": username},
            {"$set": {"liked_books": [book_with_category], "username": username}},
            upsert=True
        )
    return True

def get_liked_books(username):
    user_library = get_user_library_collection()
    doc = user_library.find_one({"username": username})
    return doc.get("liked_books", []) if doc else []

def unlike_book_for_user(username, isbn):
    user_library = get_user_library_collection()
    # Remove book with matching isbn13 or isbn
    user_library.update_one(
        {"username": username},
        {"$pull": {"liked_books": {"$or": [{"isbn13": isbn}, {"isbn": isbn}]}}}
    )

def update_book_category(username, isbn, new_category):
    user_library = get_user_library_collection()
    
    # Update the category of the book with matching ISBN
    result = user_library.update_one(
        {
            "username": username,
            "liked_books": {"$elemMatch": {"$or": [{"isbn13": isbn}, {"isbn": isbn}]}}
        },
        {
            "$set": {
                "liked_books.$.category": new_category,
                "liked_books.$.last_updated": datetime.now().isoformat()
            }
        }
    )
    
    return result.modified_count > 0

def get_books_by_category(username, category):
    user_library = get_user_library_collection()
    
    # Use aggregation to filter books by category
    pipeline = [
        {"$match": {"username": username}},
        {"$unwind": "$liked_books"},
        {"$match": {"liked_books.category": category}},
        {"$replaceRoot": {"newRoot": "$liked_books"}}
    ]
    
    books = list(user_library.aggregate(pipeline))
    return books

def display_message(message):
    if message["role"] != "system":
        if message["role"] == "assistant":
            avatar = "AI"
            avatar_class = "assistant-avatar"
            message_class = "assistant-message"
            
            if "한국어 답변:" in message["content"]:
                parts = message["content"].split("한국어 답변:", 1)
                english_part = parts[0].strip()
                korean_part = parts[1].strip() if len(parts) > 1 else ""
                
                st.markdown(f"""
                <div class="message-with-avatar">
                    <div class="message-avatar {avatar_class}">{avatar}</div>
                    <div class="chat-message {message_class}">
                        {english_part}
                        <div class="korean-text">
                            <span class="korean-label">한국어 답변:</span><br>
                            {korean_part}
                        </div>
                        <div class="message-timestamp">Now</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="message-with-avatar">
                    <div class="message-avatar {avatar_class}">{avatar}</div>
                    <div class="chat-message {message_class}">
                        {message["content"]}
                        <div class="message-timestamp">Now</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            avatar = "You"
            avatar_class = "user-avatar"
            message_class = "user-message"
            
            st.markdown(f"""
            <div class="message-with-avatar">
                <div class="message-avatar {avatar_class}">{avatar}</div>
                <div class="chat-message {message_class}">
                    {message["content"]}
                    <div class="message-timestamp">Now</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def call_hyperclova_api(messages, api_key):
    """Helper function to call HyperCLOVA API with correct headers"""
    try:
        endpoint = "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": messages,
            "maxTokens": 1024,
            "temperature": 0.7,
            "topP": 0.8,
        }
        
        response = requests.post(endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return result['result']['message']['content']
        else:
            st.error(f"Error connecting to HyperCLOVA API: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error connecting to HyperCLOVA API: {e}")
        return None

def display_book_card(book, index):
    """Display a book card with like and image functionality, using MongoDB for liked books."""
    # Handle both old format (direct keys) and new format (nested in 'doc')
    if "doc" in book:
        info = book["doc"]
    else:
        info = book

    cols = st.columns([1, 3])
    with cols[0]:
        image_url = info.get("bookImageURL", "")
        if image_url:
            st.image(image_url, width=120)
        else:
            st.markdown("""
            <div style="width: 100px; height: 150px; background: linear-gradient(135deg, #2c3040, #363c4e); 
                        display: flex; align-items: center; justify-content: center; border-radius: 5px;">
                <span style="color: #b3b3cc;">No Image</span>
            </div>
            """, unsafe_allow_html=True)
    with cols[1]:
        title = info.get('bookname') or info.get('bookName', '제목 없음')
        authors = info.get('authors') or info.get('author', '저자 없음')
        publisher = info.get('publisher', '출판사 없음')
        year = info.get('publication_year') or info.get('publicationYear', '연도 없음')
        loan_count = info.get('loan_count') or info.get('loanCount', 0)
        isbn13 = info.get('isbn13') or info.get('isbn', 'unknown')

        st.markdown(f"""
        <div style="padding-left: 10px; margin-top: 0;">
            <div style="font-size: 1.2em; font-weight: bold; color: #333; margin-bottom: 8px;">{title}</div>
            <div style="margin-bottom: 4px;"><strong>저자:</strong> {authors}</div>
            <div style="margin-bottom: 4px;"><strong>출판사:</strong> {publisher}</div>
            <div style="margin-bottom: 4px;"><strong>출간년도:</strong> {year}</div>
            <div style="margin-bottom: 8px;"><strong>대출 횟수:</strong> {loan_count}</div>
        </div>
        """, unsafe_allow_html=True)

        btn_col1, btn_col2 = st.columns([2, 1])
        with btn_col1:
            if st.button(f"이 책에 대해 더 알아보기", key=f"details_{isbn13}_{index}"):
                st.session_state.selected_book = info
                st.session_state.app_stage = "discuss_book"
                st.rerun()
        with btn_col2:
            # Check if this book is already liked
            liked_books = get_liked_books(st.session_state.username)
            already_liked = any((b.get("isbn13") or b.get("isbn")) == isbn13 for b in liked_books)
            if already_liked:
                st.button("❤️", key=f"liked_{isbn13}_{index}", help="내 서재에 추가됨", disabled=True)
            else:
                if st.button("❤️", key=f"like_{isbn13}_{index}", help="내 서재에 추가"):
                    # Store the book in MongoDB with consistent ISBN field
                    book_data = info.copy()
                    book_data['isbn13'] = isbn13
                    like_book_for_user(st.session_state.username, book_data)
                    st.success("서재에 추가되었습니다!")
                    st.rerun()

    # Add a subtle separator between cards
    st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid #000;'>", unsafe_allow_html=True)


import re

def extract_keywords_with_hyperclova(user_input, api_key):
    """Extract and detect if the user is asking for books by a specific author or a genre (robust natural language support)"""
    if not api_key:
        return detect_author_or_genre_fallback(user_input)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Enhanced multi-language author detection prompt with more natural language examples
    author_detection_prompt = f"""
사용자 입력 분석: "{user_input}"

다음 기준으로 요청 유형을 정확히 판단해주세요:

**작가 검색 패턴:**
- 한국 작가: "박경리", "김영하", "무라카미 하루키", "황석영 작품", "이문열 소설"
- 외국 작가: "Stephen King", "J.K. Rowling", "Agatha Christie", "셰익스피어", "헤밍웨이"
- 작가 관련 표현: "~의 작품", "~가 쓴", "~저자", "~작가의 책", "books by ~", "recommend me books by ~", "show me books by ~", "books written by ~", "author ~", "작가 ~", "저자 ~", "책 by ~"

**장르/주제 검색 패턴:**
- 문학 장르: "로맨스", "추리소설", "판타지", "SF", "호러", "스릴러"
- 주제 분야: "역사책", "철학서", "과학도서", "경제학", "자기계발"
- 일반적 표현: "~에 관한 책", "~분야", "~관련 도서"

**판단 규칙:**
1. 사람의 이름(성+이름 또는 단일명)이 포함 → 작가 검색
2. 문학 장르나 학문 분야명만 포함 → 장르 검색
3. 애매한 경우 문맥으로 판단

응답 형식:
- 작가 검색: "AUTHOR:작가이름"
- 장르 검색: "GENRE"

예시:
"무라카미 하루키 신작" → AUTHOR:무라카미 하루키
"미스터리 소설 추천해줘" → GENRE
"스티븐 킹" → AUTHOR:스티븐 킹
"철학 관련 서적" → GENRE
"해리포터 작가 책" → AUTHOR:J.K. Rowling
"recommend me books by Stephen King" → AUTHOR:Stephen King
"show me books by Agatha Christie" → AUTHOR:Agatha Christie
"books written by 헤밍웨이" → AUTHOR:헤밍웨이
"author 무라카미 하루키" → AUTHOR:무라카미 하루키
"""
    
    data_detection = {
        "messages": [
            {
                "role": "system",
                "content": "당신은 도서 검색 요청을 정확히 분석하는 전문가입니다. 사용자가 특정 작가의 책을 찾는지, 아니면 특정 장르나 주제의 책을 찾는지 명확하게 구분해야 합니다. 작가 이름이 포함되면 작가 검색, 장르나 주제만 언급되면 장르 검색으로 판단합니다. 반드시 아래 응답 형식만 사용하세요."
            },
            {
                "role": "user", 
                "content": author_detection_prompt
            }
        ],
        "maxTokens": 150,
        "temperature": 0.1,
        "topP": 0.3,
    }
    
    try:
        # API call for request type detection
        import requests
        response = requests.post(
            "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003",
            headers=headers,
            json=data_detection,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            detection_result = result['result']['message']['content'].strip()
            
            # Parse the response more robustly
            if "AUTHOR:" in detection_result:
                author_name = detection_result.split("AUTHOR:")[-1].strip()
                author_name = author_name.replace('"', '').replace("'", '').strip()
                if author_name:
                    return ("AUTHOR", author_name)
            elif "GENRE" in detection_result:
                return ("GENRE", user_input)
            
            # If response format is unexpected, try fallback
            return enhanced_fallback_extraction(user_input)
        else:
            # Optionally: log or print error
            return enhanced_fallback_extraction(user_input)
            
    except Exception as e:
        # Optionally: log or print error
        return enhanced_fallback_extraction(user_input)

def enhanced_fallback_extraction(user_input):
    """Improved fallback method to detect if input is author name or genre without API"""
    normalized_input = user_input.lower().strip()
    
    # Author-related regex patterns (English & Korean)
    author_patterns = [
        r'books by ([\w\s\.\-가-힣]+)',         # books by Stephen King
        r'by author ([\w\s\.\-가-힣]+)',        # by author J.K. Rowling
        r'author ([\w\s\.\-가-힣]+)',           # author 무라카미 하루키
        r'작가[ ]*([\w\s\.\-가-힣]+)',           # 작가 무라카미 하루키
        r'저자[ ]*([\w\s\.\-가-힣]+)',           # 저자 김영하
        r'([\w\s\.\-가-힣]+)의 작품',            # 김영하의 작품
        r'([\w\s\.\-가-힣]+)가 쓴',              # 김영하가 쓴
        r'([\w\s\.\-가-힣]+) 작가의 책',          # 김영하 작가의 책
        r'books written by ([\w\s\.\-가-힣]+)', # books written by Hemingway
    ]
    for pattern in author_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            author_name = match.group(1).strip()
            # Remove trailing words like '책', '소설', etc.
            author_name = re.sub(r'(책|소설|작품|author|저자|작가)$', '', author_name, flags=re.IGNORECASE).strip()
            if author_name:
                return ("AUTHOR", author_name)
    
    # Fallback to your original logic if no pattern matched
    return detect_author_or_genre_fallback(user_input)

def detect_author_or_genre_fallback(user_input):
    """Original fallback method with minor improvements"""
    normalized_input = user_input.lower().strip()
    author_keywords = [
        '작가', '저자', '작품', '소설가', '시인', '문학가',
        'author', 'writer', 'books by', 'novels by', 'works by',
        '가 쓴', '의 작품', '의 책', '의 소설'
    ]
    genre_keywords = [
        '소설', '로맨스', '추리', '미스터리', '판타지', 'sf', '공상과학',
        '역사', '철학', '경제', '과학', '자기계발', '에세이', '시집',
        'romance', 'mystery', 'fantasy', 'thriller', 'horror', 
        'philosophy', 'history', 'economics', 'science'
    ]
    for keyword in author_keywords:
        if keyword in normalized_input:
            clean_name = user_input
            for remove_word in ['작가', '저자', '작품', '소설', '책', 'author', 'writer', 'books by']:
                clean_name = re.sub(rf'\b{re.escape(remove_word)}\b', '', clean_name, flags=re.IGNORECASE)
            clean_name = clean_name.strip()
            if clean_name:
                return ("AUTHOR", clean_name)
    korean_surnames = ['김', '박', '이', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '류', '전']
    has_korean_surname = any(surname in user_input for surname in korean_surnames)
    words = user_input.split()
    has_western_name_pattern = len(words) >= 2 and any(word[0].isupper() and len(word) > 1 for word in words)
    famous_authors = [
        '하루키', '헤밍웨이', '톨스토이', '도스토옙스키', '카프카', '조이스',
        'king', 'rowling', 'christie', 'shakespeare', 'hemingway'
    ]
    has_famous_author = any(author.lower() in normalized_input for author in famous_authors)
    if has_korean_surname or has_western_name_pattern or has_famous_author:
        genre_indicators = ['추천', '소개', '목록', '리스트', '종류', '분야', '관련']
        is_genre_request = any(indicator in normalized_input for indicator in genre_indicators) and \
                          any(genre in normalized_input for genre in genre_keywords)
        if not is_genre_request:
            return ("AUTHOR", user_input.strip())
    if any(genre in normalized_input for genre in genre_keywords):
        return ("GENRE", user_input)
    if len(words) <= 3 and (has_korean_surname or has_western_name_pattern):
        return ("AUTHOR", user_input.strip())
    return ("GENRE", user_input)

def extract_genre_keywords(user_input, api_key, dtl_kdc_dict, headers):
    """Original genre-based keyword extraction logic"""
    # First attempt - exact keyword matching
    categories_list = []
    for code, label in dtl_kdc_dict.items():
        categories_list.append(f"- {code}: {label}")
    
    categories_text = "\n".join(categories_list)
    
    # First prompt - look for exact keywords
    prompt_exact = f"""
다음은 전체 도서 분류 코드 목록입니다:
{categories_text}

사용자 입력: "{user_input}"

위의 전체 목록에서 사용자 입력과 정확히 일치하는 키워드나 분류명을 찾아주세요.
예를 들어:
- "영문학" → 영미문학 관련 코드
- "역사" → 역사 관련 코드  
- "소설" → 소설 관련 코드
- "철학" → 철학 관련 코드

정확한 일치가 있으면 해당 코드번호만 반환하세요. 정확한 일치가 없으면 "NO_EXACT_MATCH"를 반환하세요.
"""
    
    data_exact = {
        "messages": [
            {
                "role": "system",
                "content": "당신은 도서 분류 전문가입니다. 전체 분류 목록에서 정확한 키워드 일치를 찾아 코드번호만 반환합니다."
            },
            {
                "role": "user", 
                "content": prompt_exact
            }
        ],
        "maxTokens": 50,
        "temperature": 0.1,
        "topP": 0.5,
    }
    
    try:
        # First API call - exact matching
        response = requests.post(
            "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003",
            headers=headers,
            json=data_exact,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            extracted_code = result['result']['message']['content'].strip()
            extracted_code = extracted_code.replace('"', '').replace("'", '').strip()
            
            # If exact match found and exists in dictionary
            if extracted_code != "NO_EXACT_MATCH" and extracted_code in dtl_kdc_dict:
                return extracted_code, dtl_kdc_dict[extracted_code]
            
            # If no exact match, try second attempt with similarity
            prompt_similar = f"""
사용자 입력: "{user_input}"

다음은 사용할 수 있는 도서 분류 코드들입니다:
{categories_text}

정확한 일치가 없으므로, 사용자 입력의 의미와 가장 유사한 분류 코드를 찾아주세요.
의미상 연관성을 고려하여 가장 적절한 코드를 선택하세요.

예를 들어:
- "책 추천" → 일반적인 문학이나 총류 관련 코드
- "경제 관련" → 경제학 관련 코드
- "건강" → 의학이나 건강 관련 코드
- "요리" → 요리, 음식 관련 코드

가장 유사한 코드번호만 반환하세요.
"""
            
            data_similar = {
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 도서 분류 전문가입니다. 의미적 유사성을 바탕으로 가장 적절한 분류 코드를 찾아 반환합니다."
                    },
                    {
                        "role": "user", 
                        "content": prompt_similar
                    }
                ],
                "maxTokens": 50,
                "temperature": 0.3,
                "topP": 0.7,
            }
            
            # Second API call - similarity matching
            response2 = requests.post(
                "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003",
                headers=headers,
                json=data_similar,
                timeout=30
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                similar_code = result2['result']['message']['content'].strip()
                similar_code = similar_code.replace('"', '').replace("'", '').strip()
                
                if similar_code in dtl_kdc_dict:
                    return similar_code, dtl_kdc_dict[similar_code]
                else:
                    # Try to find partial matches
                    return find_best_dtl_code_fallback(user_input, dtl_kdc_dict, similar_code)
            else:
                return find_best_dtl_code_fallback(user_input, dtl_kdc_dict)
        else:
            st.warning(f"HyperCLOVA API error: {response.status_code}")
            return find_best_dtl_code_fallback(user_input, dtl_kdc_dict)
            
    except Exception as e:
        st.warning(f"Keyword extraction failed: {e}")
        return find_best_dtl_code_fallback(user_input, dtl_kdc_dict)

# --- New function to get books by author ---
def get_books_by_author(author_name, auth_key, page_no=1, page_size=10):
    """Get books by specific author using Library API"""
    url = "http://data4library.kr/api/srchBooks"
    params = {
        "authKey": auth_key,
        "author": author_name,
        "pageNo": page_no,
        "pageSize": page_size,
        "format": "json"
    }
    
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            response_data = r.json()
            
            # Check if response has the expected structure
            if "response" in response_data and "docs" in response_data["response"]:
                docs = response_data["response"]["docs"]
                
                # Handle case where docs might be a single dict instead of list
                if isinstance(docs, dict):
                    docs = [docs]
                elif not isinstance(docs, list):
                    return []
                
                # Extract and clean book data
                books = []
                for doc in docs:
                    # Handle nested 'doc' structure if it exists
                    if "doc" in doc:
                        book_data = doc["doc"]
                    else:
                        book_data = doc
                    
                    # Extract book information with fallback values
                    book_info = {
                        "bookname": book_data.get("bookname", book_data.get("bookName", "Unknown Title")),
                        "authors": book_data.get("authors", book_data.get("author", "Unknown Author")),
                        "publisher": book_data.get("publisher", "Unknown Publisher"),
                        "publication_year": book_data.get("publication_year", book_data.get("publicationYear", "Unknown Year")),
                        "isbn13": book_data.get("isbn13", book_data.get("isbn", "")),
                        "loan_count": int(book_data.get("loan_count", book_data.get("loanCount", 0))),
                        "bookImageURL": book_data.get("bookImageURL", ""),
                        "bookDtlUrl": book_data.get("bookDtlUrl", "")
                    }
                    books.append(book_info)
                
                # Sort by publication year (descending) and then by loan count
                books = sorted(books, key=lambda x: (x.get("publication_year", "0"), x["loan_count"]), reverse=True)
                return books
            else:
                st.error(f"No books found for author: {author_name}")
                return []
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse API response: {e}")
        return []
    except Exception as e:
        st.error(f"Error processing API response: {e}")
        return []
    
    return []
    
def find_best_dtl_code_fallback(user_query, dtl_kdc_dict, ai_suggested_code=None):
    """Fallback method to find the best matching DTL KDC code"""
    best_score = 0
    best_code = None
    best_label = ""
    
    # If AI suggested a code but it wasn't exact, try to find similar codes
    if ai_suggested_code:
        for code, label in dtl_kdc_dict.items():
            if ai_suggested_code in code or code in ai_suggested_code:
                return code, label
    
    # Original similarity matching
    for code, label in dtl_kdc_dict.items():
        # Check similarity with the label
        score = SequenceMatcher(None, user_query.lower(), label.lower()).ratio()
        
        # Also check if any word from user query is in the label
        user_words = user_query.lower().split()
        for word in user_words:
            if len(word) > 1 and word in label.lower():
                score += 0.3  # Boost score for word matches
        
        if score > best_score:
            best_score = score
            best_code = code
            best_label = label
    
    return best_code, best_label if best_score > 0.2 else (None, None)

def get_dtl_kdc_code(user_query, api_key=None):
    """Enhanced DTL KDC code detection with better author/genre classification"""
    if api_key:
        try:
            # Use HyperCLOVA for classification
            result = extract_keywords_with_hyperclova(user_query, api_key)
            
            # Handle author requests
            if isinstance(result, tuple) and len(result) == 2 and result[0] == "AUTHOR":
                author_name = result[1]
                st.info(f"🔍 Searching for books by author: **{author_name}**")
                return "AUTHOR", author_name
            
            # Handle genre requests
            elif isinstance(result, tuple) and len(result) == 2 and result[0] == "GENRE":
                user_input = result[1]
                st.info(f"📚 Searching for books in genre/topic: **{user_input}**")
                
                # Use the existing genre extraction logic
                code, label = extract_genre_keywords(user_input, api_key, dtl_kdc_dict, {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                })
                
                if code and label:
                    st.success(f"✅ Found category: **{label}** (Code: {code})")
                    return code, label
                else:
                    st.warning("⚠️ Could not find a matching category. Please try being more specific with genres like 'romance novels', 'mystery books', or 'philosophy books'.")
                    return None, None
            
            # Fallback if HyperCLOVA result is unexpected
            else:
                st.info("🔄 HyperCLOVA response unclear, using fallback analysis...")
                return handle_fallback_classification(user_query)
                
        except Exception as e:
            st.warning(f"❌ HyperCLOVA processing failed: {e}. Using fallback search...")
            return handle_fallback_classification(user_query)
    
    # No API key available
    else:
        st.info("🔍 Using fallback search without AI assistance...")
        return handle_fallback_classification(user_query)

def handle_fallback_classification(user_query):
    """Handle classification when HyperCLOVA is not available or fails"""
    fallback_result = detect_author_or_genre_fallback(user_query)
    
    if fallback_result[0] == "AUTHOR":
        author_name = fallback_result[1]
        st.info(f"👤 Detected author search: **{author_name}**")
        return "AUTHOR", author_name
    else:
        # Try genre matching with dtl_kdc_dict
        code, label = find_best_dtl_code_fallback(user_query, dtl_kdc_dict)
        if code and label:
            st.success(f"📖 Found category: **{label}** (Code: {code})")
            return code, label
        else:
            st.warning("⚠️ Could not find a matching category. Please try being more specific with:\n"
                      "- **Author names**: 'Stephen King', '무라카미 하루키', 'J.K. Rowling'\n"
                      "- **Genres**: 'romance novels', 'mystery books', 'philosophy', 'history'")
            return None, None

            
# --- Query library API for books by DTL KDC code ---
def get_books_by_dtl_kdc(dtl_kdc_code, auth_key, page_no=1, page_size=10):
    """Get books using DTL KDC code"""
    url = "http://data4library.kr/api/loanItemSrch"
    params = {
        "authKey": auth_key,
        "startDt": "2000-01-01",
        "endDt": datetime.now().strftime("%Y-%m-%d"),
        "format": "json",
        "pageNo": page_no,
        "pageSize": page_size,
        "dtl_kdc": dtl_kdc_code  # Use dtl_kdc parameter
    }
    
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            response_data = r.json()
            
            # Check if response has the expected structure
            if "response" in response_data:
                docs = response_data["response"].get("docs", [])
                
                # Handle case where docs might be a single dict instead of list
                if isinstance(docs, dict):
                    docs = [docs]
                elif not isinstance(docs, list):
                    return []
                
                # Extract and clean book data
                books = []
                for doc in docs:
                    # Handle nested 'doc' structure if it exists
                    if "doc" in doc:
                        book_data = doc["doc"]
                    else:
                        book_data = doc
                    
                    # Extract book information with fallback values
                    book_info = {
                        "bookname": book_data.get("bookname", book_data.get("bookName", "Unknown Title")),
                        "authors": book_data.get("authors", book_data.get("author", "Unknown Author")),
                        "publisher": book_data.get("publisher", "Unknown Publisher"),
                        "publication_year": book_data.get("publication_year", book_data.get("publicationYear", "Unknown Year")),
                        "isbn13": book_data.get("isbn13", book_data.get("isbn", "")),
                        "loan_count": int(book_data.get("loan_count", book_data.get("loanCount", 0))),
                        "bookImageURL": book_data.get("bookImageURL", "")
                    }
                    books.append(book_info)
                
                # Sort by loan count (descending)
                books = sorted(books, key=lambda x: x["loan_count"], reverse=True)
                return books
            else:
                st.error(f"Unexpected API response structure: {response_data}")
                return []
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse API response: {e}")
        return []
    except Exception as e:
        st.error(f"Error processing API response: {e}")
        return []
    
    return []

# --- Sidebar (as provided) ---
def setup_sidebar():
    with st.sidebar:
        # Location selection at the top
        st.markdown("### 📍 Location (Optional)")
        location_options = ["전체 지역 (All Regions)"] + [f"{loc['city']} {loc['district']}" for loc in location_data]
        
        selected_location = st.selectbox(
            "જ⁀➴ Select your location:",
            location_options,
            key="location_selector"
        )
        
        # Store selected location code in session state
        if selected_location == "전체 지역 (All Regions)":
            st.session_state.selected_location_code = None
            st.session_state.selected_location_name = "전체 지역"
        else:
            # Find the matching location code
            for loc in location_data:
                if f"{loc['city']} {loc['district']}" == selected_location:
                    st.session_state.selected_location_code = loc['code']
                    st.session_state.selected_location_name = selected_location
                    break
        
        st.markdown("---")
        
        # Add custom CSS for multi-line buttons with equal width
        st.markdown("""
        <style>
        .stButton > button {
            white-space: pre-line !important;
            height: auto !important;
            padding: 12px 16px !important;
            line-height: 1.3 !important;
            width: 100% !important;
            min-width: 200px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if st.button("좋아하는 책들\nMY LIBRARY"):
            st.session_state.app_stage = "show_liked_books"
            st.rerun()
        
        if st.button("토론 페이지\nDiscussion Page", key="open_discussion"):
            st.session_state.show_discussion = True
            st.session_state.app_stage = "discussion_page"
            st.rerun()
        
        # New button for checking book availability in region
        if st.button("도서 이용 가능 여부\nCheck Book Availability"):
            st.session_state.app_stage = "check_regional_books"
            st.rerun()
        
        # Reset button
        if st.button("다시 시작하기\nREFRESH PAGE"):
            st.session_state.messages = [
                {"role": "system", "content": "You are a helpful AI assistant specializing in book recommendations. For EVERY response, you must answer in BOTH English and Korean. First provide the complete answer in English, then provide '한국어 답변:' followed by the complete Korean translation of your answer."}
            ]
            st.session_state.app_stage = "welcome"
            st.session_state.user_genre = ""
            st.session_state.user_age = ""
            st.session_state.selected_book = None
            st.session_state.showing_books = False
            st.rerun()
        
        st.markdown("""
        <div style="text-align: center; margin-top: 30px; padding: 10px;">
            <p style="color: #b3b3cc; font-size: 0.8rem;">
                HyperCLOVA X 🤝 한국 도서관 API
            </p>
        </div>
        """, unsafe_allow_html=True)

        
# --- Process follow-up questions with HyperCLOVA ---
def process_followup_with_hyperclova(user_input, api_key):
    """Process follow-up questions using HyperCLOVA API"""
    if not api_key:
        return "Please provide your HyperCLOVA API key in the sidebar to get detailed responses.\n\n한국어 답변: 자세한 답변을 받으려면 사이드바에서 HyperCLOVA API 키를 제공해 주세요."
    
    # Create context from previous messages
    conversation_context = ""
    recent_messages = st.session_state.messages[-5:]  # Get last 5 messages for context
    for msg in recent_messages:
        if msg["role"] != "system":
            conversation_context += f"{msg['role']}: {msg['content']}\n"
    
    prompt = f"""
이전 대화 내용:
{conversation_context}

사용자의 새로운 질문: "{user_input}"

위의 맥락을 고려하여 사용자의 질문에 대해 도움이 되는 답변을 해주세요. 
만약 새로운 도서 추천을 요청하는 것 같다면, 구체적인 장르나 주제를 제시해주세요.

답변은 영어와 한국어 모두로 제공하되, 먼저 영어로 완전한 답변을 하고, 
그 다음 "한국어 답변:" 이후에 한국어 번역을 제공하세요.
"""
    
    messages = [
        {
            "role": "system",
            "content": "당신은 도서 추천 전문가입니다. 사용자와의 대화 맥락을 이해하고 도움이 되는 답변을 제공합니다. 항상 영어와 한국어로 답변하세요."
        },
        {
            "role": "user", 
            "content": prompt
        }
    ]
    
    return call_hyperclova_api(messages, api_key)

def generate_book_introduction(book, api_key):
    """Generate an introduction about the book when first selected"""
    title = book.get('bookname') or book.get('bookName', 'Unknown Title')
    authors = book.get('authors') or book.get('author', 'Unknown Author')
    publisher = book.get('publisher', 'Unknown Publisher')
    year = book.get('publication_year') or book.get('publicationYear', 'Unknown Year')
    loan_count = book.get('loan_count') or book.get('loanCount', 0)
    
    if not api_key:
        return f"Let's discuss '{title}' by {authors}! This book was published by {publisher} in {year} and has been borrowed {loan_count} times, showing its popularity. What would you like to know about this book - its themes, plot, writing style, or would you like similar recommendations?\n\n한국어 답변: {authors}의 '{title}'에 대해 이야기해 봅시다! 이 책은 {year}년에 {publisher}에서 출간되었으며 {loan_count}번 대출되어 인기를 보여줍니다. 이 책에 대해 무엇을 알고 싶으신가요 - 주제, 줄거리, 문체, 아니면 비슷한 추천을 원하시나요?"
    
    book_context = f"Book: {title} by {authors}, published by {publisher} in {year}, with {loan_count} loans"
    
    messages = [
        {
            "role": "system",
            "content": "You are a knowledgeable book expert. For EVERY response, answer in BOTH English and Korean. First provide complete English answer, then '한국어 답변:' with Korean translation. Provide an engaging introduction about the book."
        },
        {
            "role": "user", 
            "content": f"Please provide an engaging introduction about this book: {book_context}. Talk about what makes this book interesting, its potential themes, and invite the user to ask questions about it. Keep it conversational and welcoming."
        }
    ]
    
    response = call_hyperclova_api(messages, api_key)
    if response:
        return response
    else:
        # Fallback if API fails
        return f"Let's explore '{title}' by {authors}! This book from {publisher} ({year}) has {loan_count} loans, indicating its appeal to readers. I'm here to discuss anything about this book - from plot details to thematic analysis. What aspect interests you most?\n\n한국어 답변: {authors}의 '{title}'을 탐험해 봅시다! {publisher}({year})의 이 책은 {loan_count}번의 대출로 독자들에게 어필하고 있음을 보여줍니다. 줄거리 세부사항부터 주제 분석까지 이 책에 대한 모든 것을 논의할 준비가 되어 있습니다. 어떤 측면에 가장 관심이 있으신가요?"

def process_book_question(book, question, api_key, conversation_history):
    """Process specific questions about a book using HyperCLOVA with improved context handling"""
    if not api_key:
        return "Please provide your HyperCLOVA API key in the sidebar to get detailed responses about this book.\n\n한국어 답변: 이 책에 대한 자세한 답변을 받으려면 사이드바에서 HyperCLOVA API 키를 제공해 주세요."
    
    title = book.get('bookname') or book.get('bookName', 'Unknown Title')
    authors = book.get('authors') or book.get('author', 'Unknown Author')
    publisher = book.get('publisher', 'Unknown Publisher')
    year = book.get('publication_year') or book.get('publicationYear', 'Unknown Year')
    loan_count = book.get('loan_count') or book.get('loanCount', 0)
    
    # Build comprehensive conversation context
    context_string = ""
    if conversation_history:
        # Include more context - last 6 messages for better continuity
        recent_history = conversation_history[-6:] if len(conversation_history) >= 6 else conversation_history
        for msg in recent_history:
            role = "사용자" if msg["role"] == "user" else "AI"
            context_string += f"{role}: {msg['content']}\n\n"
    
    book_info = f"제목: '{title}', 저자: {authors}, 출판사: {publisher}, 출간년도: {year}, 인기도: {loan_count}회 대출"
    
    # Enhanced prompt with better context integration
    enhanced_prompt = f"""
현재 논의 중인 도서 정보:
{book_info}

이전 대화 내용:
{context_string}

사용자의 새로운 질문: "{question}"

위의 도서와 이전 대화 맥락을 모두 고려하여 사용자의 질문에 대해 상세하고 도움이 되는 답변을 제공해주세요.

답변 지침:
1. 이전 대화의 맥락을 참고하여 연속성 있는 답변을 제공하세요
2. 책의 내용, 주제, 등장인물, 문체, 문화적 배경 등에 대해 구체적으로 설명하세요
3. 필요시 유사한 책 추천도 포함하세요
4. 영어로 완전한 답변을 먼저 제공하고, 그 다음 "한국어 답변:" 이후에 한국어 번역을 제공하세요

답변은 상세하고 통찰력 있게 작성해주세요.
"""
    
    messages = [
        {
            "role": "system",
            "content": f"당신은 '{title}' by {authors}에 대해 논의하는 지식이 풍부한 도서 전문가입니다. 이전 대화의 맥락을 기억하고 연속성 있는 답변을 제공합니다. 모든 답변은 영어와 한국어 모두로 제공하며, 먼저 영어로 완전한 답변을 하고 그 다음 '한국어 답변:'으로 한국어 번역을 제공합니다. 도서의 주제, 줄거리 요소, 등장인물 분석, 문체, 문화적 맥락, 유사한 도서 추천 등을 포함한 상세하고 통찰력 있는 정보를 제공합니다."
        },
        {
            "role": "user",
            "content": enhanced_prompt
        }
    ]
    
    try:
        response = call_hyperclova_api(messages, api_key)
        if response:
            return response
        else:
            return f"I'd be happy to continue our discussion about '{title}', but I'm having trouble connecting to the AI service right now. Could you try asking your question again?\n\n한국어 답변: '{title}'에 대한 논의를 계속하고 싶지만 지금 AI 서비스에 연결하는 데 문제가 있습니다. 질문을 다시 해보시겠어요?"
    except Exception as e:
        st.error(f"Error processing question: {e}")
        return f"I encountered an error while processing your question about '{title}'. Please try rephrasing your question or check your API connection.\n\n한국어 답변: '{title}'에 대한 질문을 처리하는 중 오류가 발생했습니다. 질문을 다시 표현하거나 API 연결을 확인해 주세요."
    
@st.cache_resource
def load_location_data():
    """Load location data from dtl_region.json"""
    try:
        with open("dtl_region.json", encoding="utf-8") as f:
            location_data = json.load(f)
        return location_data
    except FileNotFoundError:
        st.error("dtl_region.json file not found")
        return []

# Add this after loading dtl_kdc_dict
location_data = load_location_data()

def get_popular_books_by_location(location_code, auth_key, page_no=1, page_size=20, dtl_kdc_code=None):
    """Get popular books by location with optional genre filtering using Library API"""
    url = "http://data4library.kr/api/loanItemSrchByLib"
    
    if location_code:
        params = {
            "authKey": auth_key,
            "dtl_region": location_code,
            "pageNo": page_no,
            "pageSize": page_size,
            "format": "json"
        }
        
        # Add genre filter if provided
        if dtl_kdc_code:
            params["dtl_kdc"] = dtl_kdc_code
            
    else:
        # If no location, get overall popular books
        url = "http://data4library.kr/api/loanItemSrch"
        params = {
            "authKey": auth_key,
            "startDt": "2023-01-01",
            "endDt": datetime.now().strftime("%Y-%m-%d"),
            "pageNo": page_no,
            "pageSize": page_size,
            "format": "json"
        }
        
        # Add genre filter if provided
        if dtl_kdc_code:
            params["dtl_kdc"] = dtl_kdc_code
    
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            response_data = r.json()
            
            if "response" in response_data:
                docs = response_data["response"].get("docs", [])
                
                if isinstance(docs, dict):
                    docs = [docs]
                elif not isinstance(docs, list):
                    return []
                
                books = []
                for doc in docs:
                    if "doc" in doc:
                        book_data = doc["doc"]
                    else:
                        book_data = doc
                    
                    book_info = {
                        "bookname": book_data.get("bookname", "Unknown Title"),
                        "authors": book_data.get("authors", "Unknown Author"),
                        "publisher": book_data.get("publisher", "Unknown Publisher"),
                        "publication_year": book_data.get("publication_year", "Unknown Year"),
                        "isbn13": book_data.get("isbn13", ""),
                        "loan_count": int(book_data.get("loan_count", 0)),
                        "bookImageURL": book_data.get("bookImageURL", "")
                    }
                    books.append(book_info)
                
                return sorted(books, key=lambda x: x["loan_count"], reverse=True)
            else:
                return []
    except Exception as e:
        st.error(f"Error fetching books: {e}")
        return []
    
    return []


def check_book_availability_in_region(isbn, location_code, auth_key):
    """Check if a book is available in libraries in a specific region"""
    if not location_code:
        return False, "No location specified"
    
    url = "http://data4library.kr/api/libSrchByBook"
    params = {
        "authKey": auth_key,
        "isbn": isbn,
        "region": location_code[:2],  # Use first 2 digits for region
        "format": "json"
    }
    
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            response_data = r.json()
            
            if "response" in response_data:
                libs = response_data["response"].get("libs", [])
                if isinstance(libs, dict):
                    libs = [libs]
                
                return len(libs) > 0, f"Available in {len(libs)} libraries"
            else:
                return False, "No libraries found"
    except Exception as e:
        return False, f"Error checking availability: {e}"
    
    return False, "Unknown error"
