"""
AI Assistant Views.

Customer endpoint: POST /api/ai/chat/
Vendor endpoint: POST /api/ai/vendor-chat/
Conversation history: GET /api/ai/conversations/
"""

import sys
import os

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.ai_assistant.models import AIConversation, AssistantType
from core.permissions import IsCustomer, IsVendorOrAdmin


class CustomerChatView(APIView):
    """
    Customer AI shopping assistant.
    Send a message and get product recommendations, search help, and order tracking.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["ai"],
        summary="Chat with the customer AI shopping assistant",
        description=(
            "Send a message to SmartMall's AI shopping assistant. "
            "It can search for products, recommend items, compare prices, "
            "find nearby shops, and track your orders. "
            "Pass `conversation_id` to continue an existing conversation."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Your message to the assistant"},
                    "conversation_id": {"type": "string", "description": "Optional: continue existing conversation"},
                    "lat": {"type": "number", "description": "Your latitude for location-aware search"},
                    "lng": {"type": "number", "description": "Your longitude for location-aware search"},
                },
                "required": ["message"],
            }
        },
    )
    def post(self, request):
        message = request.data.get("message", "").strip()
        if not message:
            return Response({"detail": "message is required."}, status=400)

        conversation_id = request.data.get("conversation_id")
        lat = request.data.get("lat")
        lng = request.data.get("lng")

        # Load or create conversation
        if conversation_id:
            conversation = AIConversation.objects.filter(
                pk=conversation_id,
                user=request.user,
                assistant_type=AssistantType.CUSTOMER,
            ).first()
            if not conversation:
                return Response({"detail": "Conversation not found."}, status=404)
        else:
            conversation = AIConversation.objects.create(
                user=request.user,
                assistant_type=AssistantType.CUSTOMER,
                title=message[:60],
            )

        # Add sys.path for ai module
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            from ai.assistant.customer_assistant import CustomerAssistant

            assistant = CustomerAssistant(
                customer_id=str(request.user.pk),
                customer_lat=float(lat) if lat else None,
                customer_lng=float(lng) if lng else None,
            )

            result = assistant.chat(
                message=message,
                conversation_history=conversation.history,
            )

            # Save updated history (exclude tool call internals for storage efficiency)
            clean_history = [
                m for m in result["conversation_history"]
                if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
            ]
            conversation.history = clean_history
            conversation.save(update_fields=["history", "updated_at"])

            return Response({
                "response": result["response"],
                "conversation_id": str(conversation.pk),
                "error": result.get("error"),
            })

        except ImportError as exc:
            return Response({
                "response": "AI assistant module not available.",
                "conversation_id": str(conversation.pk),
                "error": str(exc),
            })
        except Exception as exc:
            return Response({
                "response": "Something went wrong with the AI assistant.",
                "conversation_id": str(conversation.pk),
                "error": str(exc),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VendorChatView(APIView):
    """
    Vendor AI business assistant.
    Ask about sales, stock levels, pending orders, and demand forecasts.
    """
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(
        tags=["ai"],
        summary="Chat with the vendor AI business assistant",
        description=(
            "Send a message to SmartMall's vendor AI assistant. "
            "It can summarise your sales, flag low stock, show pending orders, "
            "and provide demand forecasts. Pass `business_id` for your shop."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "business_id": {"type": "string", "description": "Your business UUID"},
                    "conversation_id": {"type": "string", "description": "Optional: continue existing conversation"},
                },
                "required": ["message", "business_id"],
            }
        },
    )
    def post(self, request):
        message = request.data.get("message", "").strip()
        business_id = request.data.get("business_id", "").strip()

        if not message:
            return Response({"detail": "message is required."}, status=400)
        if not business_id:
            return Response({"detail": "business_id is required."}, status=400)

        # Verify vendor owns this business
        from apps.businesses.models import Business
        business = Business.objects.filter(pk=business_id).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)
        if not request.user.is_staff and business.owner_id != request.user.id:
            return Response({"detail": "Not your business."}, status=403)

        conversation_id = request.data.get("conversation_id")
        if conversation_id:
            conversation = AIConversation.objects.filter(
                pk=conversation_id, user=request.user,
                assistant_type=AssistantType.VENDOR,
            ).first()
            if not conversation:
                return Response({"detail": "Conversation not found."}, status=404)
        else:
            conversation = AIConversation.objects.create(
                user=request.user,
                assistant_type=AssistantType.VENDOR,
                title=message[:60],
            )

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            from ai.assistant.vendor_assistant import VendorAssistant

            assistant = VendorAssistant(business_id=business_id)
            result = assistant.chat(
                message=message,
                conversation_history=conversation.history,
            )

            clean_history = [
                m for m in result["conversation_history"]
                if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
            ]
            conversation.history = clean_history
            conversation.save(update_fields=["history", "updated_at"])

            return Response({
                "response": result["response"],
                "conversation_id": str(conversation.pk),
                "error": result.get("error"),
            })

        except Exception as exc:
            return Response({
                "response": "Something went wrong with the AI assistant.",
                "conversation_id": str(conversation.pk),
                "error": str(exc),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationListView(APIView):
    """List user's AI conversation history."""
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["ai"], summary="List my AI conversations")
    def get(self, request):
        conversations = AIConversation.objects.filter(
            user=request.user, is_active=True
        ).values("id", "assistant_type", "title", "created_at", "updated_at")

        return Response({
            "conversations": [
                {
                    "id": str(c["id"]),
                    "type": c["assistant_type"],
                    "title": c["title"],
                    "created_at": c["created_at"],
                    "updated_at": c["updated_at"],
                }
                for c in conversations[:20]
            ]
        })


class SmartSearchView(APIView):
    """ML-ranked product search endpoint."""
    permission_classes = []

    @extend_schema(
        tags=["ai"],
        summary="Smart ML-ranked product search",
        description="Search products with ML ranking — combines relevance, distance, rating, stock and promotions.",
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "q parameter required."}, status=400)

        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        limit = min(int(request.query_params.get("limit", 10)), 50)

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            from ml.ranking.ranker import SearchRanker
            ranker = SearchRanker()
            results = ranker.rank(
                query=query,
                lat=float(lat) if lat else None,
                lng=float(lng) if lng else None,
                limit=limit,
            )
            return Response(results)
        except Exception as exc:
            return Response({"error": str(exc)}, status=500)


class DemandForecastView(APIView):
    """ML demand forecast for vendor products."""
    permission_classes = [IsAuthenticated, IsVendorOrAdmin]

    @extend_schema(
        tags=["ai"],
        summary="Get ML demand forecast for your products",
        description="Returns restock recommendations ranked by urgency based on 90 days of sales data and seasonal patterns.",
    )
    def get(self, request, business_id):
        from apps.businesses.models import Business
        business = Business.objects.filter(pk=business_id).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)
        if not request.user.is_staff and business.owner_id != request.user.id:
            return Response({"detail": "Not your business."}, status=403)

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            from ml.demand.predictor import DemandPredictor
            predictor = DemandPredictor()
            forecast = predictor.forecast_for_business(business_id=str(business_id))
            return Response(forecast)
        except Exception as exc:
            return Response({"error": str(exc)}, status=500)
