using Microsoft.Extensions.Logging;
using Shop.Application.Abstractions;
using Shop.Domain.Orders;

namespace Shop.Application.Features.Orders;

public sealed class SetOrderStateCommandHandler(IOrderRepository orders, ILogger<SetOrderStateCommandHandler> logger)
{
    public async Task<Result> Handle(SetOrderStateCommand request, CancellationToken cancellationToken)
    {
        var change = await orders.SetStateAsync(
            request.OrderNumber, (OrderState)request.State, request.Note?.Trim() ?? string.Empty, cancellationToken);

        switch (change.Outcome)
        {
            case OrderStateOutcome.NotFound:
                return Result.NotFound(OrderErrorCodes.OrderNotFound);
            case OrderStateOutcome.NotAllowed:
                return Result.Conflict(OrderErrorCodes.StateChangeNotAllowed);
            default:
                logger.LogInformation("Order {OrderNumber} moved from {Previous} to {State}",
                    request.OrderNumber, change.Previous, request.State);
                return Result.Success();
        }
    }
}

public static class OrderErrorCodes
{
    public const string OrderNotFound = "order-not-found";
    public const string StateChangeNotAllowed = "state-change-not-allowed";
}
