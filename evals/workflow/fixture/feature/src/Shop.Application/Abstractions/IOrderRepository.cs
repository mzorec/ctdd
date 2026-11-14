using Shop.Application.Features.Orders;
using Shop.Domain.Orders;

namespace Shop.Application.Abstractions;

/// <summary>Access to orders: the read, and the checked state write.</summary>
public interface IOrderRepository
{
    Task<Order?> GetAsync(string orderNumber, CancellationToken cancellationToken);

    /// <summary>Checks the move and writes the state and the note in one call.</summary>
    Task<OrderStateChange> SetStateAsync(string orderNumber, OrderState state, string note, CancellationToken cancellationToken);
}

public sealed record Order(string OrderNumber, OrderState State, string Note);
