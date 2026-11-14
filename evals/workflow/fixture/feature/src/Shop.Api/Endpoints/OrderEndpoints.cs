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

        group.MapPut("/orders/{orderNumber}/state", async (
                string orderNumber, SetOrderStateBody body, SetOrderStateCommandHandler handler, CancellationToken ct) =>
                (await handler.Handle(new SetOrderStateCommand(orderNumber, body.State, body.Note), ct)).ToHttpResult())
            .WithName("SetOrderState")
            .WithSummary("Moves an order to Packed or Shipped.")
            .WithDescription("Sets the order's state when the move is allowed, and stores the note sent with it.")
            .Produces(StatusCodes.Status204NoContent)
            .ProducesProblem(StatusCodes.Status400BadRequest)
            .ProducesProblem(StatusCodes.Status404NotFound)
            .ProducesProblem(StatusCodes.Status409Conflict);

        return group;
    }
}

public sealed record SetOrderStateBody(SettableOrderState State, string? Note);
