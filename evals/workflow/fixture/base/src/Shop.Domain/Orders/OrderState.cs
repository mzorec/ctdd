namespace Shop.Domain.Orders;

/// <summary>Where an order is in fulfilment. The numbers are stored.</summary>
public enum OrderState
{
    Created = 10,
    Paid = 30,
    Packed = 40,
    Shipped = 50,
    Cancelled = 90,
}
