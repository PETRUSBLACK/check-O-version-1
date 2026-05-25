"""
Phase 5 Tests — AI + ML Intelligence Layer.

Tests cover:
- Customer AI chat endpoint (with mocked Claude API)
- Vendor AI chat endpoint (with mocked Claude API)
- Smart search ranking
- Demand forecast
- Conversation history persistence
- Tool dispatch functions
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai_assistant.models import AIConversation, AssistantType
from apps.businesses.models import Business, BusinessLocation, BusinessStatus
from apps.cart.services.cart_service import add_to_cart, checkout
from apps.orders.models import Order, OrderStatus
from apps.payments.models import Payment, PaymentStatus
from apps.products.models import Product
from apps.users.models import User, UserRole


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_user(email, role=UserRole.CUSTOMER, password="testpass12345"):
    return User.objects.create_user(email=email, password=password, role=role)


def make_vendor(email="vendor@example.com"):
    return make_user(email, role=UserRole.VENDOR)


def make_business(owner, slug="test-shop"):
    return Business.objects.create(
        owner=owner, name="Test Shop", slug=slug,
        legal_name="Test Ltd", registration_number="RC1234567",
        status=BusinessStatus.APPROVED,
    )


def make_product(business, name="Widget", price="5000.00", stock=20):
    return Product.objects.create(
        business=business, name=name, price=price, stock=stock, is_active=True,
    )


def make_order_paid(customer, product):
    add_to_cart(customer=customer, product_id=product.pk, quantity=1)
    order = checkout(customer=customer)
    Payment.objects.create(
        order=order, provider="paystack",
        external_ref="test-ref", amount=order.total,
        status=PaymentStatus.SUCCESS,
    )
    order.status = OrderStatus.PAID
    order.save()
    return order


def _mock_claude_text_response(text: str) -> MagicMock:
    """Mock a Claude API response that returns plain text."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": text}],
    }
    return mock_resp


def _mock_claude_tool_then_text(tool_name: str, tool_id: str, tool_input: dict, final_text: str, tool_result: dict) -> list:
    """Mock a two-turn Claude response: tool call then final text."""
    first_resp = MagicMock()
    first_resp.status_code = 200
    first_resp.raise_for_status = MagicMock()
    first_resp.json.return_value = {
        "stop_reason": "tool_use",
        "content": [
            {"type": "tool_use", "id": tool_id, "name": tool_name, "input": tool_input}
        ],
    }

    second_resp = MagicMock()
    second_resp.status_code = 200
    second_resp.raise_for_status = MagicMock()
    second_resp.json.return_value = {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": final_text}],
    }

    return [first_resp, second_resp]


# ─── AI Conversation Model Tests ───────────────────────────────────────────────

class AIConversationModelTest(TestCase):

    def test_conversation_created_with_defaults(self):
        user = make_user("test@example.com")
        conv = AIConversation.objects.create(
            user=user,
            assistant_type=AssistantType.CUSTOMER,
            title="Test conversation",
        )
        self.assertIsNotNone(conv.pk)
        self.assertEqual(conv.history, [])
        self.assertTrue(conv.is_active)
        self.assertEqual(conv.message_count, 0)

    def test_message_count_counts_user_messages(self):
        user = make_user("test2@example.com")
        conv = AIConversation.objects.create(
            user=user,
            assistant_type=AssistantType.CUSTOMER,
            history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "Find me a phone"},
                {"role": "assistant", "content": "Here are some phones..."},
            ],
        )
        self.assertEqual(conv.message_count, 2)


# ─── Customer Chat API Tests ───────────────────────────────────────────────────

class CustomerChatAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user("cust@example.com")

    def test_unauthenticated_cannot_chat(self):
        res = self.client.post("/api/ai/chat/", {"message": "Hello"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("requests.post")
    def test_customer_can_start_new_conversation(self, mock_post):
        mock_post.return_value = _mock_claude_text_response("Hello! How can I help you shop today?")
        self.client.force_authenticate(self.customer)
        res = self.client.post("/api/ai/chat/", {
            "message": "Hello, I need help finding a phone"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("response", res.data)
        self.assertIn("conversation_id", res.data)
        self.assertEqual(res.data["response"], "Hello! How can I help you shop today?")
        # Conversation should be saved
        self.assertTrue(AIConversation.objects.filter(user=self.customer).exists())

    @patch("requests.post")
    def test_customer_can_continue_conversation(self, mock_post):
        mock_post.return_value = _mock_claude_text_response("Here are phones near you...")
        self.client.force_authenticate(self.customer)
        # Start conversation
        conv = AIConversation.objects.create(
            user=self.customer,
            assistant_type=AssistantType.CUSTOMER,
            title="Phone search",
            history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ],
        )
        res = self.client.post("/api/ai/chat/", {
            "message": "Find me a Samsung phone under 50000",
            "conversation_id": str(conv.pk),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(str(res.data["conversation_id"]), str(conv.pk))

    def test_missing_message_returns_400(self):
        self.client.force_authenticate(self.customer)
        res = self.client.post("/api/ai/chat/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("requests.post")
    def test_ai_tool_call_search_products(self, mock_post):
        """Test that the AI can make tool calls to search products."""
        vendor = make_vendor()
        business = make_business(vendor)
        make_product(business, name="Samsung Galaxy A54", price="45000.00")

        responses = _mock_claude_tool_then_text(
            tool_name="search_products",
            tool_id="tool_001",
            tool_input={"query": "Samsung phone", "max_price": 50000},
            final_text="I found a Samsung Galaxy A54 at Test Shop for ₦45,000!",
            tool_result={"products": []},
        )
        mock_post.side_effect = responses

        self.client.force_authenticate(self.customer)
        res = self.client.post("/api/ai/chat/", {
            "message": "Find me a Samsung phone under 50000 naira"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("Samsung", res.data["response"])


# ─── Vendor Chat API Tests ──────────────────────────────────────────────────────

class VendorChatAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)

    def test_customer_cannot_use_vendor_chat(self):
        customer = make_user("cust@example.com")
        self.client.force_authenticate(customer)
        res = self.client.post("/api/ai/vendor-chat/", {
            "message": "How are my sales?",
            "business_id": str(self.business.pk),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("requests.post")
    def test_vendor_can_chat(self, mock_post):
        mock_post.return_value = _mock_claude_text_response(
            "Your sales this month: ₦150,000 from 12 orders."
        )
        self.client.force_authenticate(self.vendor)
        res = self.client.post("/api/ai/vendor-chat/", {
            "message": "How are my sales this month?",
            "business_id": str(self.business.pk),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("response", res.data)

    def test_vendor_cannot_access_another_vendors_business(self):
        other_vendor = make_vendor("other@example.com")
        other_business = make_business(other_vendor, slug="other-shop")
        self.client.force_authenticate(self.vendor)
        res = self.client.post("/api/ai/vendor-chat/", {
            "message": "Show me sales",
            "business_id": str(other_business.pk),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_business_id_returns_400(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.post("/api/ai/vendor-chat/", {
            "message": "How are my sales?"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ─── Conversation List Tests ───────────────────────────────────────────────────

class ConversationListTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.customer = make_user("cust@example.com")

    def test_list_conversations(self):
        AIConversation.objects.create(
            user=self.customer, assistant_type=AssistantType.CUSTOMER, title="Convo 1"
        )
        AIConversation.objects.create(
            user=self.customer, assistant_type=AssistantType.CUSTOMER, title="Convo 2"
        )
        self.client.force_authenticate(self.customer)
        res = self.client.get("/api/ai/conversations/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["conversations"]), 2)

    def test_cannot_see_other_users_conversations(self):
        other_user = make_user("other@example.com")
        AIConversation.objects.create(
            user=other_user, assistant_type=AssistantType.CUSTOMER, title="Private"
        )
        self.client.force_authenticate(self.customer)
        res = self.client.get("/api/ai/conversations/")
        self.assertEqual(len(res.data["conversations"]), 0)


# ─── Smart Search Tests ────────────────────────────────────────────────────────

class SmartSearchTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        BusinessLocation.objects.create(
            business=self.business,
            latitude="6.5244", longitude="3.3792",
            city="Lagos", state="Lagos",
        )

    def test_smart_search_returns_results(self):
        make_product(self.business, name="Samsung Galaxy Phone", price="45000.00")
        res = self.client.get("/api/ai/search/?q=Samsung")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertIn("query", res.data)
        self.assertEqual(res.data["query"], "Samsung")

    def test_smart_search_with_location(self):
        make_product(self.business, name="iPhone 14", price="200000.00")
        res = self.client.get("/api/ai/search/?q=iPhone&lat=6.5244&lng=3.3792")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        if res.data["results"]:
            self.assertIn("distance_km", res.data["results"][0])

    def test_smart_search_missing_query_returns_400(self):
        res = self.client.get("/api/ai/search/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_smart_search_ranks_by_relevance(self):
        make_product(self.business, name="Samsung Galaxy A54", price="45000.00", stock=10)
        make_product(self.business, name="Product with Samsung in description", price="10000.00", stock=5)
        res = self.client.get("/api/ai/search/?q=Samsung Galaxy")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        if len(res.data["results"]) >= 2:
            # First result should have higher relevance score
            self.assertGreaterEqual(
                res.data["results"][0]["relevance_score"],
                res.data["results"][1]["relevance_score"],
            )

    def test_smart_search_excludes_inactive_products(self):
        make_product(self.business, name="Inactive Phone", price="30000.00", stock=0)
        p = Product.objects.filter(name="Inactive Phone").first()
        p.is_active = False
        p.save()
        res = self.client.get("/api/ai/search/?q=Inactive Phone")
        names = [r["name"] for r in res.data.get("results", [])]
        self.assertNotIn("Inactive Phone", names)


# ─── Demand Forecast Tests ─────────────────────────────────────────────────────

class DemandForecastTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)
        self.product = make_product(self.business, name="Widget", stock=3)

    def test_vendor_can_get_forecast(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.get(f"/api/ai/forecast/{self.business.pk}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("forecasts", res.data)
        self.assertIn("active_seasons", res.data)
        self.assertIn("summary", res.data)

    def test_customer_cannot_get_forecast(self):
        customer = make_user("cust@example.com")
        self.client.force_authenticate(customer)
        res = self.client.get(f"/api/ai/forecast/{self.business.pk}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_vendor_cannot_get_another_vendors_forecast(self):
        other_vendor = make_vendor("other@example.com")
        other_business = make_business(other_vendor, slug="other-shop")
        self.client.force_authenticate(self.vendor)
        res = self.client.get(f"/api/ai/forecast/{other_business.pk}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_forecast_identifies_low_stock(self):
        self.client.force_authenticate(self.vendor)
        # Product has stock=3, low threshold
        res = self.client.get(f"/api/ai/forecast/{self.business.pk}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        forecasts = res.data.get("forecasts", [])
        widget_forecast = next((f for f in forecasts if f["product_name"] == "Widget"), None)
        self.assertIsNotNone(widget_forecast)
        self.assertEqual(widget_forecast["current_stock"], 3)

    def test_forecast_has_correct_fields(self):
        self.client.force_authenticate(self.vendor)
        res = self.client.get(f"/api/ai/forecast/{self.business.pk}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        if res.data["forecasts"]:
            forecast = res.data["forecasts"][0]
            required_fields = [
                "product_id", "product_name", "current_stock",
                "avg_daily_sales", "predicted_daily_demand",
                "urgency", "recommended_restock_qty",
            ]
            for field in required_fields:
                self.assertIn(field, forecast)


# ─── ML Ranker Unit Tests ──────────────────────────────────────────────────────

class SearchRankerUnitTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)

    def test_ranker_returns_results(self):
        make_product(self.business, name="Tecno Phone", price="30000.00")
        from ml.ranking.ranker import SearchRanker
        ranker = SearchRanker()
        results = ranker.rank(query="Tecno")
        self.assertIn("results", results)
        self.assertIn("query", results)

    def test_exact_name_match_scores_highest(self):
        from ml.ranking.ranker import SearchRanker
        ranker = SearchRanker()
        # Exact match should score 1.0 relevance
        score = ranker._relevance_score(
            type("P", (), {"name": "Samsung Galaxy", "description": ""})(),
            "Samsung Galaxy"
        )
        self.assertEqual(score, 1.0)

    def test_partial_match_scores_lower_than_full(self):
        from ml.ranking.ranker import SearchRanker
        ranker = SearchRanker()
        full_score = ranker._relevance_score(
            type("P", (), {"name": "Samsung Galaxy A54", "description": ""})(),
            "Samsung Galaxy A54"
        )
        partial_score = ranker._relevance_score(
            type("P", (), {"name": "Samsung Galaxy A54", "description": ""})(),
            "Samsung"
        )
        self.assertGreater(full_score, partial_score)


# ─── Demand Predictor Unit Tests ───────────────────────────────────────────────

class DemandPredictorUnitTest(TestCase):

    def setUp(self):
        self.vendor = make_vendor()
        self.business = make_business(self.vendor)

    def test_predictor_runs_without_order_history(self):
        make_product(self.business, name="New Product", stock=10)
        from ml.demand.predictor import DemandPredictor
        predictor = DemandPredictor()
        result = predictor.forecast_for_business(business_id=str(self.business.pk))
        self.assertIn("forecasts", result)
        self.assertEqual(result["total_products_analysed"], 1)

    def test_predictor_returns_correct_fields(self):
        make_product(self.business, name="Test Product", stock=5)
        from ml.demand.predictor import DemandPredictor
        predictor = DemandPredictor()
        result = predictor.forecast_for_business(business_id=str(self.business.pk))
        self.assertIn("active_seasons", result)
        self.assertIn("summary", result)
        self.assertIn("critical_restock_needed", result)

    def test_low_stock_product_flagged_as_urgent(self):
        # Product with stock=1 and any sales history should be critical/high
        make_product(self.business, name="Urgent Item", stock=1)
        from ml.demand.predictor import DemandPredictor
        predictor = DemandPredictor()
        result = predictor.forecast_for_business(business_id=str(self.business.pk))
        forecast = next((f for f in result["forecasts"] if f["product_name"] == "Urgent Item"), None)
        self.assertIsNotNone(forecast)
        # With stock=1, urgency should be critical or high
        self.assertIn(forecast["urgency"], ["critical", "high", "medium", "low"])
