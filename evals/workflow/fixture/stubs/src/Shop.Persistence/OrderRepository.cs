using Shop.Application.Abstractions;
using Shop.Application.Features.Orders;
using Shop.Domain.Orders;

namespace Shop.Persistence;

internal sealed class OrderRepository(Database database) : IOrderRepository
{
    public Task<Order?> GetAsync(string orderNumber, CancellationToken cancellationToken) =>
        database.QuerySingleOrDefaultAsync<Order>(
            "SELECT OrderNumber, State, Note FROM Orders WHERE OrderNumber = @orderNumber",
            new { orderNumber }, cancellationToken);

    // Compile-only stub from step 7; replaced in Phase 1. It reports `Set` and writes nothing.
    public Task<OrderStateChange> SetStateAsync(
        string orderNumber, OrderState state, string note, CancellationToken cancellationToken) =>
        Task.FromResult(new OrderStateChange(OrderStateOutcome.Set));
}
