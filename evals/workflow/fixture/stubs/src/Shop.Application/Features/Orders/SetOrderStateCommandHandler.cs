using Shop.Application.Abstractions;

namespace Shop.Application.Features.Orders;

/// <summary>Compile-only stub from step 7; replaced in Phase 2. It answers success and calls nothing.</summary>
public sealed class SetOrderStateCommandHandler(IOrderRepository orders, ILogger<SetOrderStateCommandHandler> logger)
{
    public Task<Result> Handle(SetOrderStateCommand request, CancellationToken cancellationToken) =>
        Task.FromResult(Result.Success());
}

public static class OrderErrorCodes
{
    public const string OrderNotFound = "order-not-found";
    public const string StateChangeNotAllowed = "state-change-not-allowed";
}
