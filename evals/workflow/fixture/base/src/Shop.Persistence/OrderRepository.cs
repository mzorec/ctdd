using Shop.Application.Abstractions;
using Shop.Domain.Orders;

namespace Shop.Persistence;

internal sealed class OrderRepository(Database database) : IOrderRepository
{
    public Task<Order?> GetAsync(string orderNumber, CancellationToken cancellationToken) =>
        database.QuerySingleOrDefaultAsync<Order>(
            "SELECT OrderNumber, State, Note FROM Orders WHERE OrderNumber = @orderNumber",
            new { orderNumber }, cancellationToken);
}
