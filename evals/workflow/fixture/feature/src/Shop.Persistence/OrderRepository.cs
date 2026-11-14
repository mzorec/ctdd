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

    public async Task<OrderStateChange> SetStateAsync(
        string orderNumber, OrderState state, string note, CancellationToken cancellationToken)
    {
        await using var transaction = await database.BeginAsync(cancellationToken);
        var current = await transaction.QuerySingleOrDefaultAsync<OrderState?>(
            "SELECT State FROM Orders WITH (UPDLOCK) WHERE OrderNumber = @orderNumber", new { orderNumber });
        if (current is null)
        {
            return new OrderStateChange(OrderStateOutcome.NotFound, default);
        }

        // Paid may only move to Packed; nothing moves backwards.
        var allowed = current == OrderState.Paid ? state == OrderState.Packed : current >= OrderState.Packed && state >= current;
        if (!allowed)
        {
            return new OrderStateChange(OrderStateOutcome.NotAllowed, current.Value);
        }

        await transaction.ExecuteAsync(
            "UPDATE Orders SET State = @state, Note = @note WHERE OrderNumber = @orderNumber",
            new { orderNumber, state, note });
        await transaction.CommitAsync(cancellationToken);
        return new OrderStateChange(OrderStateOutcome.Set, current.Value);
    }
}
