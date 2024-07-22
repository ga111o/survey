from main import db  # Flask 애플리케이션이 정의된 파일을 import 합니다.

# 데이터베이스 초기화 함수
def init_db():
    db.create_all()  # 모든 테이블 생성
    print("데이터베이스가 초기화되었습니다.")

if __name__ == '__main__':
    init_db()
