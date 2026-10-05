from rest_framework.views import APIView
from rest_framework.response import Response

class SendCalendarReminderView(APIView):
    def post(self, request):
        email_arg = request.data.get('email')
        return Response({'msg': email_arg})

class MockRequest:
    def __init__(self, data):
        self.data = data

mock_req = MockRequest({'email': 'test@example.com'})
view = SendCalendarReminderView()
try:
    res = view.post(mock_req)
    print('SUCCESS:', res.data)
except Exception as e:
    print('ERROR:', e)
