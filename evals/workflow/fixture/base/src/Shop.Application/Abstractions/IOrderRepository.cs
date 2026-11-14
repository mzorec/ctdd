using Shop.Domain.Orders;

namespace Shop.Application.Abstractions;

/// <summary>Read access to orders.</summary>
public interface IOrderRepository
{
    Task<Order?> GetAsync(string orderNumber, CancellationToken cancellationToken);
}

public sealed record Order(string OrderNumber, OrderState State, string Note);
