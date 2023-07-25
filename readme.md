# Easy Health Checker
수많은 서버 PC의 상태를 한눈에 볼 수 있도록 하는 client & server 응용 프로그램.
서버의 저장장치 용량/CPU/램 과 웹서버, WAS, 기타 응용 어플리케이션들의 상태를 관리할 수 있는 프로젝트.

# How to use ?
실시간 상태를 확인하고자 하는 PC에서는 client의 코드를 빌드하여 exe로 추출한 뒤 사용하고, 모든 상태를 관리하는 메인 서버 혹은 PC에서는 server의 코드를 이용하면 됩니다.

# Develop Environment
- python 3.9
- fastAPI

# Feature
- 별도의 소스코드 수정 없이 간편하게 관리 대상을 추가/제거 가능.
- CPU / RAM / 저장장치 사용률과 응용 어플리케이션(WAS, 웹서버 등)의 status를 실시간으로 관리.
- server에서 제공하는 web을 통해 상황 모니터링이 가능하고, 결과를 csv 파일로 제공받을 수 있음.
![health_1](https://github.com/jungsungwook/easy-healthchecker/assets/20926860/21c92f38-94c6-4b32-9c26-daf51557693d)
![health_2](https://github.com/jungsungwook/easy-healthchecker/assets/20926860/15a23a8a-8d2c-40d5-8520-99c1cc177868)
