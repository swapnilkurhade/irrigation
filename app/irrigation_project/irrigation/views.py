from django.http import JsonResponse
from .controller import run_irrigation_check

def run_irrigation_view(request):
    result = run_irrigation_check()
    return JsonResponse(result)
