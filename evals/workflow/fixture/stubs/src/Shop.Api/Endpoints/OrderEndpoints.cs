using Shop.Application.Abstractions;
using Shop.Application.Features.Orders;

namespace Shop.Api.Endpoints;

public static class OrderEndpoints
{
    public static RouteGroupBuilder MapOrders(this RouteGroupBuilder group)
    {
        group.MapGet("/orders/{orderNumber}", async (string orderNumber, IOrderRepository orders, CancellationToken ct) =>
                await orders.GetAsync(orderNumber, ct) is { } order ? Results.Ok(order) : Results.NotFound())
            .WithName("GetOrder")
            .WithSummary("Reads one order.")
            .WithDescription("Returns the order with the given number.");

        // Compile-only stub from step 7; replaced in Phase 3. The route is registered so the
        // endpoint tests reach the host; it declares no responses yet.
        group.MapPut("/orders/{orderNumber}/state", async (
                string orderNumber, SetOrderStateBody body, SetOrderStateCommandHandler handler, CancellationToken ct) =>
                (await handler.Handle(new SetOrderStateCommand(orderNumber, body.State, body.Note), ct)).ToHttpResult());

        return group;
    }
}

public sealed record SetOrderStateBody(SettableOrderState State, string? Note);
