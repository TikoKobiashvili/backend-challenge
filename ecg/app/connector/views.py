from rest_framework import status, viewsets, permissions
from connector import serializers
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .permissions import HasECGDataPermission
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied

from connector import operations


@extend_schema(tags=['user'])
class UserLoginView(APIView):
    """
    User login view
    """
    permission_classes = (AllowAny,)

    serializer_class = serializers.UserLoginSerializer

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description='Request success'
            ),
            400: OpenApiResponse(description='Invalid value'),
            403: OpenApiResponse(description='Permission Denied'),
            500: OpenApiResponse(description='Internal server error'),
        },
        request=serializer_class
    )
    def post(self, request):
        serializer = serializers.UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        return Response({'token': token.key}, status=status.HTTP_200_OK)


@extend_schema(tags=['user'])
class UserRegistrationView(APIView):
    """
    User registration view
    """
    permission_classes = (AllowAny,)

    serializer_class = serializers.UserRegistrationSerializer

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description='Request success'
            ),
            400: OpenApiResponse(description='Invalid value'),
            403: OpenApiResponse(description='Permission Denied'),
            500: OpenApiResponse(description='Internal server error'),
        },
        request=serializer_class
    )
    def post(self, request, *args, **kwargs):
        # Other than admin that was required, this endpoint also can create/register users
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['ecg_monitoring'])
class ECGView(viewsets.ViewSet):
    """
    ECG Monitoring application service
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    serializer_class_response = serializers.ECGResponseSerializer
    serializer_class_request = serializers.ECGModelSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view/method requires.
        """
        if self.action == 'retrieve_zero_crossing':
            return [permissions.IsAuthenticated(), HasECGDataPermission()]
        else:
            return [permissions.IsAuthenticated()]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description='Request success'
            ),
            400: OpenApiResponse(description='Invalid value'),
            403: OpenApiResponse(description='Permission Denied'),
            500: OpenApiResponse(description='Internal server error'),
        },
        request=serializer_class_request
    )
    def create(self, request):
        """
        Receives ECG data for processing
        """
        operations.ECGOperations().create_ecg_record(ecg_data=request.data, context={'request': request})

        return Response(f'ECG record created successfully', status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description='Request success', response=serializer_class_response
            ),
            404: OpenApiResponse(description='Resource not available'),
            400: OpenApiResponse(description='Invalid value'),
            403: OpenApiResponse(description='Permission Denied'),
            500: OpenApiResponse(description='Internal server error'),
        },
    )
    def retrieve_zero_crossing(self, request, ecg_id):
        """
         Returns the number of times each ECG channel crosses zero
        """
        ecg_instance = operations.ECGOperations().get_ecg_instance(ecg_id)

        # Check if the authenticated user has permission to retrieve this ECG data
        self.check_object_permissions(request, ecg_instance)

        response = operations.ECGOperations().get_zero_crossing_count(ecg_instance)

        return Response(response, status=status.HTTP_200_OK)
