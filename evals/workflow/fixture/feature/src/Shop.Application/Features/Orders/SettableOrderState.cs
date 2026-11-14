namespace Shop.Application.Features.Orders;

/// <summary>The states a client may set. The numbers match `OrderState`.</summary>
public enum SettableOrderState
{
    Packed = 40,
    Shipped = 50,
}
